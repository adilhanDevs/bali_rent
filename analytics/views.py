import json

from rest_framework import permissions, response, serializers, status, views

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


class AdminRevenueAnalyticsView(views.APIView):
    permission_classes = [IsAnalyticsAdminReader]

    def get(self, request):
        payload = AnalyticsService.get_revenue_summary()
        return response.Response(RevenueAnalyticsSerializer(payload).data, status=status.HTTP_200_OK)


class AdminFunnelAnalyticsView(views.APIView):
    permission_classes = [IsAnalyticsAdminReader]

    def get(self, request):
        payload = AnalyticsService.get_funnel_summary()
        return response.Response(FunnelAnalyticsSerializer(payload).data, status=status.HTTP_200_OK)
