from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Booking
from .serializers import (
    BookingSerializer,
    BookingCalculateSerializer,
    BookingCreateSerializer,
    GuestBookingCreateSerializer,
)
from .services import BookingPriceService, BookingCreationService
from catalog.models import Vehicle
from django.shortcuts import get_object_or_404
from audit.mixins import AuditMixin

class BookingViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = Booking.objects.all().select_related('user', 'vehicle', 'delivery_address').prefetch_related('addons', 'addons__addon')
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return self.queryset
        return self.queryset.filter(user=user)

    def _request_info(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
        return {
            'ip': ip,
            'user_agent': request.META.get('HTTP_USER_AGENT'),
            'platform': request.headers.get('X-Platform', 'web'),
            'country': request.headers.get('X-Country'),
        }

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
                currency=serializer.validated_data.get('currency', 'USD'),
                request_info=self._request_info(request),
            )
            response_serializer = self.get_serializer(booking)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny], url_path='guest-create')
    def guest_create(self, request):
        serializer = GuestBookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['guest_email'].strip().lower()
        full_name = serializer.validated_data['guest_full_name'].strip()
        phone = serializer.validated_data.get('guest_phone', '').strip()

        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            return Response(
                {'error': 'This email is already registered. Please sign in to continue.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(
            username=email,
            email=email,
            password=get_random_string(24),
            full_name=full_name,
            phone=phone,
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if serializer.validated_data.get('language'):
            profile.preferred_language = serializer.validated_data['language']
            profile.save(update_fields=['preferred_language'])

        try:
            booking = BookingCreationService.create_booking(
                user=user,
                vehicle_id=serializer.validated_data['scooter_id'],
                start_at=serializer.validated_data['start_datetime'],
                end_at=serializer.validated_data['end_datetime'],
                addon_ids=serializer.validated_data.get('add_on_ids'),
                payment_method=serializer.validated_data.get('payment_method', 'online_card'),
                delivery_address_text=serializer.validated_data.get('delivery_address'),
                delivery_lat=serializer.validated_data.get('delivery_latitude'),
                delivery_lng=serializer.validated_data.get('delivery_longitude'),
                currency=serializer.validated_data.get('currency', 'USD'),
                request_info=self._request_info(request),
            )
        except ValueError as e:
            user.delete()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(user)
        response_serializer = self.get_serializer(booking)
        return Response(
            {
                'booking': response_serializer.data,
                'auth': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                },
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'full_name': user.full_name,
                    'phone': user.phone,
                },
                'created_account': True,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
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

        from notifications.services import NotificationService
        NotificationService.create_notification(
            booking.user,
            f'Booking {booking.public_number} cancelled',
            'Your booking has been cancelled successfully.',
            'booking_cancelled',
            {'booking_id': booking.id},
        )
        
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
