from rest_framework import viewsets, status, permissions, throttling
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Booking
from .serializers import BookingSerializer, BookingCalculateSerializer, BookingCreateSerializer
from .services import BookingPriceService, BookingCreationService
from catalog.models import Vehicle
from django.shortcuts import get_object_or_404
from audit.mixins import AuditMixin

class BookingViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = (
        Booking.objects.select_related('user', 'vehicle', 'delivery_address')
        .prefetch_related('addons', 'addons__addon')
        .order_by('-created_at', '-id')
    )
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_throttles(self):
        if getattr(self, 'action', None) == 'calculate':
            self.throttle_scope = 'pricing_calculate'
            self.throttle_classes = [throttling.ScopedRateThrottle]
        return super().get_throttles()

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return self.queryset
        return self.queryset.filter(user=user)

    def create(self, request, *args, **kwargs):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            booking = BookingCreationService.create_booking(
                user=request.user,
                vehicle_id=serializer.validated_data['scooter_id'],
                start_at=serializer.validated_data['start_datetime'],
                end_at=serializer.validated_data['end_datetime'],
                addon_ids=serializer.validated_data.get('add_on_ids'),
                promo_code=serializer.validated_data.get('promo_code'),
                payment_method=serializer.validated_data.get('payment_method', 'online_card'),
                delivery_address_text=serializer.validated_data.get('delivery_address'),
                delivery_lat=serializer.validated_data.get('delivery_latitude'),
                delivery_lng=serializer.validated_data.get('delivery_longitude'),
                currency=serializer.validated_data.get('currency', 'USD')
            )
            response_serializer = self.get_serializer(booking)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[permissions.AllowAny],
    )
    def calculate(self, request):
        serializer = BookingCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        vehicle = Vehicle.objects.get(id=serializer.validated_data['scooter_id'])
        
        price_details = BookingPriceService.calculate_prices(
            vehicle=vehicle,
            start_at=serializer.validated_data['start_datetime'],
            end_at=serializer.validated_data['end_datetime'],
            addon_ids=serializer.validated_data.get('add_on_ids'),
            promo_code=serializer.validated_data.get('promo_code'),
            payment_method=serializer.validated_data.get('payment_method', 'online_card'),
            delivery_lat=serializer.validated_data.get('delivery_latitude'),
            delivery_lng=serializer.validated_data.get('delivery_longitude')
        )
        
        # Format response to match required fields
        response_data = {
            'scooter_id': vehicle.id,
            'start_datetime': serializer.validated_data['start_datetime'],
            'end_datetime': serializer.validated_data['end_datetime'],
            'rental_days': price_details['rental_days'],
            'base_price': price_details['subtotal_usd'],
            'add_ons_price': price_details['addons_total_usd'],
            'delivery_price': price_details['delivery_price_usd'],
            'discount_amount': price_details['discount_usd'],
            'markup_amount': price_details['markup_usd'],
            'total_price': price_details['total_usd'],
            'promo_code': serializer.validated_data.get('promo_code') or None,
            'currency': serializer.validated_data.get('currency', 'USD'),
            'payment_method': serializer.validated_data.get('payment_method', 'online_card'),
        }
        
        return Response(response_data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.status in ['cancelled', 'completed']:
            return Response({'error': f'Cannot cancel booking in status {booking.status}'}, status=status.HTTP_400_BAD_REQUEST)
        
        before_dict = BookingSerializer(booking).data
        before_status = booking.status
        booking.status = 'cancelled'
        booking.save()
        
        # Also remove availability blocks
        booking.availability_blocks.all().delete()
        
        # Log to domain history
        from .models import BookingStatusHistory
        BookingStatusHistory.objects.create(
            booking=booking,
            old_status=before_status,
            new_status='cancelled',
            changed_by=request.user,
            comment='Cancelled by user'
        )
        
        self._log_audit(booking, 'cancel', before_dict=before_dict, after_dict=BookingSerializer(booking).data)
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
