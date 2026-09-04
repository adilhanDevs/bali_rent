from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from catalog.models import Vehicle, VehicleImage, VehicleTranslation
from bookings.models import Booking
from payments.models import Payment
from users.models import User
from catalog.serializers import AdminScooterSerializer, ScooterImageSerializer
from bookings.serializers import BookingSerializer
from users.serializers import UserSerializer, AdminUserSerializer, AdminSetUserPasswordSerializer
from support.models import FAQItem
from support.serializers import AdminFAQItemSerializer
from delivery.models import DeliveryZone, LocationSection
from delivery.serializers import AdminDeliveryZoneSerializer, LocationSectionSerializer
from sitecontent.models import SiteContentEntry
from sitecontent.serializers import SiteContentEntrySerializer
from django.utils import timezone
from audit.mixins import AuditMixin
from pricing.serializers import ScooterRentalRateSerializer


def has_team_access(user):
    if not user or not user.is_authenticated or not user.is_staff:
        return False

    if user.is_superuser or (user.role or '').strip().lower() == 'admin':
        return True

    normalized_permissions = {
        str(permission or '').strip().lower()
        for permission in (user.admin_permissions or [])
    }
    return 'team' in normalized_permissions

class AdminScooterViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = (
        Vehicle.objects.select_related('model', 'model__type')
        .prefetch_related('images', 'translations', 'rental_rates')
        .order_by('sort_order', 'id')
    )
    serializer_class = AdminScooterSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=True, methods=['get'], url_path='rental-rates')
    def rental_rates(self, request, pk=None):
        vehicle = self.get_object()
        serializer = ScooterRentalRateSerializer(vehicle.rental_rates.all(), many=True)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        vehicle = self.get_object()
        with transaction.atomic():
            Payment.objects.filter(booking__vehicle=vehicle).delete()
            Booking.objects.filter(vehicle=vehicle).delete()
            self.perform_destroy(vehicle)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def images(self, request, pk=None):
        vehicle = self.get_object()
        serializer = ScooterImageSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                image = serializer.save(vehicle=vehicle)
                if image.is_main:
                    vehicle.images.exclude(pk=image.pk).update(is_main=False)
            self._log_audit(image, 'create', after_dict=serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get', 'post'], url_path='translations')
    def translations(self, request, pk=None):
        vehicle = self.get_object()
        if request.method == 'GET':
            return Response([
                {
                    'language': t.language,
                    'title': t.title,
                    'description': t.description,
                    'rental_terms': t.rental_terms,
                    'transmission': t.transmission or '',
                    'trunk': t.trunk or '',
                    'color': t.color or '',
                }
                for t in vehicle.translations.all()
            ])
        data = request.data
        if not isinstance(data, list):
            return Response({'error': 'Expected a list of translation objects.'}, status=status.HTTP_400_BAD_REQUEST)
        for item in data:
            lang = (item.get('language') or '').strip()
            if not lang:
                continue
            VehicleTranslation.objects.update_or_create(
                vehicle=vehicle,
                language=lang,
                defaults={
                    'title': (item.get('title') or '').strip() or vehicle.title,
                    'description': (item.get('description') or '').strip(),
                    'rental_terms': (item.get('rental_terms') or '').strip(),
                    'transmission': (item.get('transmission') or '').strip() or None,
                    'trunk': (item.get('trunk') or '').strip() or None,
                    'color': (item.get('color') or '').strip() or None,
                },
            )
        self._log_audit(vehicle, 'update_translations')
        return Response({'status': 'ok'})

class AdminScooterImageViewSet(AuditMixin, viewsets.GenericViewSet):
    queryset = VehicleImage.objects.all()
    permission_classes = [permissions.IsAdminUser]

    def destroy(self, request, pk=None):
        image = self.get_object()
        self._log_audit(image, 'delete')
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

from rest_framework.pagination import PageNumberPagination

class AdminBookingPagination(PageNumberPagination):
    page_size = 500
    page_size_query_param = 'page_size'
    max_page_size = 1000

class AdminBookingViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = (
        Booking.objects.select_related('user', 'vehicle', 'vehicle__model', 'delivery_address')
        .prefetch_related('addons', 'addons__addon', 'payments')
        .order_by('-created_at', '-id')
    )
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = AdminBookingPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'vehicle', 'user']
    search_fields = ['public_number', 'contact_name', 'contact_phone', 'user__email', 'vehicle__title', 'delivery_address__address_text']
    ordering_fields = ['created_at', 'start_at', 'total_usd', 'status']

    def create(self, request, *args, **kwargs):
        from django.utils.dateparse import parse_datetime
        from decimal import Decimal
        import uuid
        from delivery.models import DeliveryAddress
        from bookings.models import AvailabilityBlock
        from bookings.services import BookingPriceService, BookingCreationService

        data = request.data
        vehicle_id = data.get('vehicle_id') or data.get('scooter_id') or data.get('vehicle')
        if not vehicle_id:
            return Response({'error': 'Vehicle is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
        except Vehicle.DoesNotExist:
            return Response({'error': f'Vehicle with id {vehicle_id} not found.'}, status=status.HTTP_400_BAD_REQUEST)

        start_str = data.get('start_at') or data.get('start_datetime')
        end_str = data.get('end_at') or data.get('end_datetime')
        if not start_str or not end_str:
            return Response({'error': 'start_datetime and end_datetime are required.'}, status=status.HTTP_400_BAD_REQUEST)

        start_at = parse_datetime(str(start_str)) if isinstance(start_str, str) else start_str
        end_at = parse_datetime(str(end_str)) if isinstance(end_str, str) else end_str

        if not start_at or not end_at:
            return Response({'error': 'Invalid date format.'}, status=status.HTTP_400_BAD_REQUEST)

        if timezone.is_naive(start_at):
            start_at = timezone.make_aware(start_at, timezone.utc)
        if timezone.is_naive(end_at):
            end_at = timezone.make_aware(end_at, timezone.utc)

        # Resolve user
        user_id = data.get('user_id') or data.get('user')
        user_email = (data.get('user_email') or data.get('email') or '').strip()
        booking_user = None
        if user_id:
            booking_user = User.objects.filter(id=user_id).first()
        elif user_email:
            booking_user = User.objects.filter(email__iexact=user_email).first()
            if not booking_user:
                booking_user = User.objects.create(
                    email=user_email,
                    full_name=data.get('contact_name', ''),
                    phone=data.get('contact_phone', ''),
                    role='client'
                )

        if not booking_user:
            booking_user = request.user

        contact_name = (data.get('contact_name') or booking_user.full_name or '').strip()
        contact_phone = (data.get('contact_phone') or booking_user.phone or '').strip()
        delivery_address_text = data.get('delivery_address')

        delivery_address = None
        if delivery_address_text:
            delivery_address = DeliveryAddress.objects.create(
                user=booking_user,
                address_text=str(delivery_address_text).strip(),
                lat=float(data.get('delivery_latitude') or 0),
                lng=float(data.get('delivery_longitude') or 0),
            )

        # Pricing
        rental_days = BookingPriceService.calculate_rental_days(start_at, end_at)
        total_price_input = data.get('total_price') or data.get('total_usd')
        if total_price_input is not None and str(total_price_input).strip() != '':
            total_usd = Decimal(str(total_price_input))
            subtotal_usd = total_usd
        else:
            base_rate = vehicle.base_price_usd or Decimal('10.00')
            total_usd = (base_rate * Decimal(rental_days)).quantize(Decimal('0.01'))
            subtotal_usd = total_usd

        payment_method = data.get('payment_method') or 'cash_on_delivery'
        payment_status = data.get('payment_status') or 'pending'
        booking_status = data.get('status') or 'confirmed'
        currency = data.get('currency') or 'USD'
        public_number = f"BK-{uuid.uuid4().hex[:8].upper()}"

        with transaction.atomic():
            booking = Booking.objects.create(
                public_number=public_number,
                user=booking_user,
                vehicle=vehicle,
                start_at=start_at,
                end_at=end_at,
                delivery_address=delivery_address,
                delivery_time=start_at,
                delivery_price_usd=Decimal('0.00'),
                payment_method=payment_method,
                payment_status=payment_status,
                currency=currency,
                subtotal_usd=subtotal_usd,
                addons_total_usd=Decimal('0.00'),
                discount_usd=Decimal('0.00'),
                markup_usd=Decimal('0.00'),
                total_usd=total_usd,
                total_display=f"${total_usd}",
                contact_name=contact_name,
                contact_phone=contact_phone,
                contact_has_telegram=bool(data.get('contact_has_telegram', False)),
                contact_has_wechat=bool(data.get('contact_has_wechat', False)),
                contact_has_whatsapp=bool(data.get('contact_has_whatsapp', False)),
                status=booking_status,
            )

            if booking.status != 'cancelled':
                AvailabilityBlock.objects.update_or_create(
                    source_booking=booking,
                    defaults={
                        'vehicle': booking.vehicle,
                        'start_at': booking.start_at,
                        'end_at': booking.end_at,
                        'type': 'booking',
                        'comment': f"Booking #{booking.public_number}",
                    }
                )

            BookingCreationService._create_support_thread(booking)

            self._log_audit(booking, 'create_admin_booking', after_dict={'public_number': public_number, 'status': booking.status})

        return Response(self.get_serializer(booking).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        return self._handle_update(request, partial=False, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self._handle_update(request, partial=True, *args, **kwargs)

    def _handle_update(self, request, partial=False, *args, **kwargs):
        from django.utils.dateparse import parse_datetime
        from decimal import Decimal
        from delivery.models import DeliveryAddress
        from bookings.models import AvailabilityBlock, BookingStatusHistory

        booking = self.get_object()
        data = request.data
        before_status = booking.status

        with transaction.atomic():
            if 'vehicle_id' in data or 'scooter_id' in data or 'vehicle' in data:
                vid = data.get('vehicle_id') or data.get('scooter_id') or data.get('vehicle')
                if vid:
                    try:
                        booking.vehicle = Vehicle.objects.get(id=vid)
                    except Vehicle.DoesNotExist:
                        return Response({'error': f'Vehicle {vid} not found.'}, status=status.HTTP_400_BAD_REQUEST)

            if 'start_at' in data or 'start_datetime' in data:
                start_val = data.get('start_at') or data.get('start_datetime')
                if start_val:
                    parsed_start = parse_datetime(str(start_val)) if isinstance(start_val, str) else start_val
                    if parsed_start:
                        if timezone.is_naive(parsed_start):
                            parsed_start = timezone.make_aware(parsed_start, timezone.utc)
                        booking.start_at = parsed_start

            if 'end_at' in data or 'end_datetime' in data:
                end_val = data.get('end_at') or data.get('end_datetime')
                if end_val:
                    parsed_end = parse_datetime(str(end_val)) if isinstance(end_val, str) else end_val
                    if parsed_end:
                        if timezone.is_naive(parsed_end):
                            parsed_end = timezone.make_aware(parsed_end, timezone.utc)
                        booking.end_at = parsed_end

            if 'delivery_time' in data:
                dtime = data.get('delivery_time')
                if dtime:
                    parsed_dtime = parse_datetime(str(dtime)) if isinstance(dtime, str) else dtime
                    if parsed_dtime:
                        if timezone.is_naive(parsed_dtime):
                            parsed_dtime = timezone.make_aware(parsed_dtime, timezone.utc)
                        booking.delivery_time = parsed_dtime
                else:
                    booking.delivery_time = None

            if 'delivery_address' in data:
                addr_text = (data.get('delivery_address') or '').strip()
                if addr_text:
                    if booking.delivery_address:
                        booking.delivery_address.address_text = addr_text
                        booking.delivery_address.save()
                    else:
                        booking.delivery_address = DeliveryAddress.objects.create(
                            user=booking.user,
                            address_text=addr_text,
                        )
                else:
                    booking.delivery_address = None

            if 'contact_name' in data:
                booking.contact_name = str(data.get('contact_name') or '').strip()
            if 'contact_phone' in data:
                booking.contact_phone = str(data.get('contact_phone') or '').strip()
            if 'contact_has_telegram' in data:
                booking.contact_has_telegram = bool(data.get('contact_has_telegram'))
            if 'contact_has_wechat' in data:
                booking.contact_has_wechat = bool(data.get('contact_has_wechat'))
            if 'contact_has_whatsapp' in data:
                booking.contact_has_whatsapp = bool(data.get('contact_has_whatsapp'))

            if 'payment_status' in data:
                booking.payment_status = str(data.get('payment_status') or booking.payment_status).strip()
            if 'payment_method' in data:
                booking.payment_method = str(data.get('payment_method') or booking.payment_method).strip()
            if 'currency' in data:
                booking.currency = str(data.get('currency') or booking.currency).strip()

            if 'total_price' in data or 'total_usd' in data:
                tprice = data.get('total_price') if 'total_price' in data else data.get('total_usd')
                if tprice is not None and str(tprice).strip() != '':
                    booking.total_usd = Decimal(str(tprice))
                    booking.subtotal_usd = booking.total_usd
                    booking.total_display = f"${booking.total_usd}"

            status_changed = False
            if 'status' in data:
                new_status = str(data.get('status') or '').strip()
                if new_status and new_status != booking.status:
                    status_changed = True
                    booking.status = new_status
                    BookingStatusHistory.objects.create(
                        booking=booking,
                        old_status=before_status,
                        new_status=new_status,
                        changed_by=self.request.user,
                        comment='Updated by admin via edit panel'
                    )

            booking.save()

            # Sync availability block
            if booking.status == 'cancelled':
                booking.availability_blocks.all().delete()
            else:
                AvailabilityBlock.objects.update_or_create(
                    source_booking=booking,
                    defaults={
                        'vehicle': booking.vehicle,
                        'start_at': booking.start_at,
                        'end_at': booking.end_at,
                        'type': 'booking',
                        'comment': f"Booking #{booking.public_number}",
                    }
                )

            self._log_audit(
                booking,
                'update_admin_booking',
                before_dict={'status': before_status},
                after_dict={'status': booking.status, 'start_at': str(booking.start_at), 'end_at': str(booking.end_at)}
            )

        return Response(self.get_serializer(booking).data)

    def get_queryset(self):
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(start_at__gte=start_date, end_at__lte=end_date)
        return queryset

    def _transition_status(self, booking, new_status, valid_previous_statuses):
        if booking.status not in valid_previous_statuses:
            return Response({'error': f'Cannot transition from {booking.status} to {new_status}'}, status=status.HTTP_400_BAD_REQUEST)
        
        before_status = booking.status
        booking.status = new_status
        booking.save()
        
        # Log to domain history
        from bookings.models import BookingStatusHistory
        BookingStatusHistory.objects.create(
            booking=booking,
            old_status=before_status,
            new_status=new_status,
            changed_by=self.request.user
        )
        
        self._log_audit(booking, 'status_transition', before_dict={'status': before_status}, after_dict={'status': new_status})
        return Response({'status': new_status})

    def destroy(self, request, *args, **kwargs):
        booking = self.get_object()
        # Payment.booking uses on_delete=PROTECT so real financial records are never
        # destroyed silently. Refuse deletion when a settled payment exists; otherwise
        # clean up the leftover non-settled attempts (pending/failed) so the booking
        # itself can be removed.
        if booking.payments.filter(status__in=['succeeded', 'refunded']).exists():
            return Response(
                {'error': 'Cannot delete a booking that has settled payments. Cancel or refund it instead.'},
                status=status.HTTP_409_CONFLICT,
            )
        with transaction.atomic():
            booking.payments.all().delete()
            self.perform_destroy(booking)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        return self._transition_status(booking, 'confirmed', ['created', 'pending_payment', 'paid'])

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.status in ['completed', 'cancelled']:
            return Response({'error': 'Booking is already completed or cancelled'}, status=status.HTTP_400_BAD_REQUEST)
        
        before_status = booking.status
        booking.status = 'cancelled'
        booking.save()
        booking.availability_blocks.all().delete()
        
        # Log to domain history
        from bookings.models import BookingStatusHistory
        BookingStatusHistory.objects.create(
            booking=booking,
            old_status=before_status,
            new_status='cancelled',
            changed_by=self.request.user,
            comment='Cancelled by admin'
        )
        
        self._log_audit(booking, 'cancel', before_dict={'status': before_status}, after_dict={'status': 'cancelled'})
        return Response({'status': 'cancelled'})

    @action(detail=True, methods=['post'], url_path='mark-delivery')
    def mark_delivery(self, request, pk=None):
        booking = self.get_object()
        return self._transition_status(booking, 'delivery', ['confirmed'])

    @action(detail=True, methods=['post'], url_path='mark-active')
    def mark_active(self, request, pk=None):
        booking = self.get_object()
        return self._transition_status(booking, 'active', ['confirmed', 'delivery'])

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        booking = self.get_object()
        return self._transition_status(booking, 'completed', ['active'])

class AdminUserViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = User.objects.select_related('profile').order_by('-id')
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAdminUser]

    def _ensure_team_access(self):
        if has_team_access(self.request.user):
            return
        raise PermissionDenied('You do not have permission to manage team members.')

    def create(self, request, *args, **kwargs):
        self._ensure_team_access()
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self._ensure_team_access()
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self._ensure_team_access()
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._ensure_team_access()
        target_user = self.get_object()
        if target_user.pk == request.user.pk:
            return Response(
                {'error': 'You cannot delete your own account from the team management screen.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'error': 'Cannot delete this user because there are protected records linked to the account.'},
                status=status.HTTP_409_CONFLICT,
            )

    @action(detail=True, methods=['post'], url_path='set-password')
    def set_password(self, request, pk=None):
        self._ensure_team_access()
        target_user = self.get_object()
        serializer = AdminSetUserPasswordSerializer(data=request.data, context={'target_user': target_user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self._log_audit(target_user, 'set_password', after_dict={'password_changed': True})
        return Response({'detail': 'Password updated successfully.'}, status=status.HTTP_200_OK)


class AdminFAQItemViewSet(viewsets.ModelViewSet):
    queryset = FAQItem.objects.prefetch_related('translations').order_by('sort_order', 'id')
    serializer_class = AdminFAQItemSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminLocationSectionViewSet(viewsets.ModelViewSet):
    queryset = LocationSection.objects.all().order_by('language')
    serializer_class = LocationSectionSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = None  # return all sections without pagination


class AdminDeliveryZoneViewSet(viewsets.ModelViewSet):
    queryset = DeliveryZone.objects.prefetch_related('translations').order_by('-is_active', 'name')
    serializer_class = AdminDeliveryZoneSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = None  # return all zones without pagination


class AdminSiteContentEntryViewSet(viewsets.ModelViewSet):
    queryset = SiteContentEntry.objects.order_by('key', 'language')
    serializer_class = SiteContentEntrySerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = None
