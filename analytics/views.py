import json
from decimal import Decimal, ROUND_HALF_UP

from rest_framework import permissions, response, serializers, status, views, throttling

from .models import AnalyticsEvent
from .services import AnalyticsService


class AnalyticsEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsEvent
        fields = ['event_name', 'payload', 'session_id', 'device_id']

    def validate_payload(self, value):
        payload_str = json.dumps(value)
        if len(payload_str) > 10240:
            raise serializers.ValidationError('Payload too large. Max 10KB.')
        return value


class RevenueAnalyticsSerializer(serializers.Serializer):
    bookings_count = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()


class FunnelAnalyticsSerializer(serializers.Serializer):
    visitors = serializers.IntegerField()
    checkout_started = serializers.IntegerField()
    bookings_created = serializers.IntegerField()
    conversion_rate = serializers.DecimalField(max_digits=8, decimal_places=2)
    checkout_conversion_rate = serializers.DecimalField(max_digits=8, decimal_places=2)


class IsAnalyticsAdminReader(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_superuser or user.role in {'admin', 'manager', 'staff'}


class AnalyticsEventCreateView(views.APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [throttling.ScopedRateThrottle]
    throttle_scope = 'analytics_events'

    def post(self, request):
        serializer = AnalyticsEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip:
            ip = ip.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        serializer.save(
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT'),
        )
        return response.Response({'status': 'captured'}, status=status.HTTP_201_CREATED)


class AdminAnalyticsRevenueView(views.APIView):
    permission_classes = [IsAnalyticsAdminReader]

    def get(self, request):
        from bookings.models import Booking
        from django.db.models import Sum, Count, Q
        from django.utils.dateparse import parse_date
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Use same logic as AnalyticsService.get_revenue_summary but with filters
        queryset = Booking.objects.filter(
            Q(payment_status='paid') | Q(status__in=['confirmed', 'delivery', 'active', 'completed'])
        ).exclude(status='cancelled')
        
        if start_date:
            parsed_start = parse_date(start_date)
            if not parsed_start:
                return response.Response({"error": "Invalid start_date format"}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(created_at__date__gte=parsed_start)
            
        if end_date:
            parsed_end = parse_date(end_date)
            if not parsed_end:
                return response.Response({"error": "Invalid end_date format"}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(created_at__date__lte=parsed_end)
            
        result = queryset.aggregate(
            bookings_count=Count('id'),
            revenue=Sum('total_usd')
        )
        
        return response.Response({
            "bookings_count": result['bookings_count'] or 0,
            "revenue": result['revenue'] or 0,
            "currency": "USD",
            "period": f"{start_date or 'all'} to {end_date or 'now'}"
        })


class AdminAnalyticsFunnelView(views.APIView):
    permission_classes = [IsAnalyticsAdminReader]

    def get(self, request):
        from django.utils.dateparse import parse_date
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = AnalyticsEvent.objects.all()
        
        if start_date:
            parsed_start = parse_date(start_date)
            if not parsed_start:
                return response.Response({"error": "Invalid start_date format"}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(created_at__date__gte=parsed_start)
            
        if end_date:
            parsed_end = parse_date(end_date)
            if not parsed_end:
                return response.Response({"error": "Invalid end_date format"}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(created_at__date__lte=parsed_end)

        events_map = {
            'page_view': 'Views',
            'start_checkout': 'Checkout Started',
            'booking_created': 'Bookings Created',
            'payment_success': 'Paid'
        }
        
        from django.db.models import Count

        event_counts = {
            row['event_name']: row['count']
            for row in queryset.filter(event_name__in=events_map.keys())
            .values('event_name')
            .annotate(count=Count('id'))
        }
        counts = {event_name: event_counts.get(event_name, 0) for event_name in events_map.keys()}

        # Specific keys for backward compatibility
        visitors = queryset.exclude(session_id__isnull=True).exclude(session_id='').values('session_id').distinct().count()
        if visitors == 0:
            visitors = counts['page_view']
            
        checkout_started = counts['start_checkout']
        bookings_created = counts['booking_created']
        
        # Calculate conversion rates for compatibility
        conversion_rate = Decimal('0.00')
        if visitors > 0:
            conversion_rate = (Decimal(bookings_created) / Decimal(visitors) * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        checkout_conversion_rate = Decimal('0.00')
        if checkout_started > 0:
            checkout_conversion_rate = (Decimal(bookings_created) / Decimal(checkout_started) * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        funnel_data = []
        prev_count = None
        for event_name, label in events_map.items():
            count = counts[event_name]
            dropoff = 0
            if prev_count is not None and prev_count > 0:
                dropoff = (
                    Decimal('100.00')
                    - (Decimal(count) / Decimal(prev_count) * Decimal('100'))
                ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            funnel_data.append({
                "step": event_name,
                "label": label,
                "count": count,
                "dropoff_percent": dropoff
            })
            prev_count = count
            
        return response.Response({
            "funnel": funnel_data,
            "visitors": visitors, # test compatibility
            "checkout_started": checkout_started,
            "bookings_created": bookings_created,
            "conversion_rate": conversion_rate,
            "checkout_conversion_rate": checkout_conversion_rate,
            "period": f"{start_date or 'all'} to {end_date or 'now'}"
        })
