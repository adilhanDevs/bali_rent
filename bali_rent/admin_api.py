from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from catalog.models import Vehicle, VehicleImage
from bookings.models import Booking
from users.models import User
from catalog.serializers import ScooterDetailSerializer, ScooterImageSerializer
from bookings.serializers import BookingSerializer
from users.serializers import UserSerializer, AdminUserSerializer
from django.utils import timezone
from audit.mixins import AuditMixin

class AdminScooterViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = Vehicle.objects.all().order_by('-created_at', '-id')
    serializer_class = ScooterDetailSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=True, methods=['post'])
    def images(self, request, pk=None):
        vehicle = self.get_object()
        serializer = ScooterImageSerializer(data=request.data)
        if serializer.is_valid():
            image = serializer.save(vehicle=vehicle)
            self._log_audit(image, 'create', after_dict=serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminScooterImageViewSet(AuditMixin, viewsets.GenericViewSet):
    queryset = VehicleImage.objects.all()
    permission_classes = [permissions.IsAdminUser]

    def destroy(self, request, pk=None):
        image = self.get_object()
        self._log_audit(image, 'delete')
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdminBookingViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = Booking.objects.all().order_by('-created_at', '-id')
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'vehicle', 'user']
    ordering_fields = ['created_at', 'start_at']

    def create(self, request, *args, **kwargs):
        # Admins also use BookingCreationService for consistency
        from bookings.serializers import BookingCreateSerializer
        from bookings.services import BookingCreationService
        
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            booking = BookingCreationService.create_booking(
                user=request.user, # Or allow admin to specify user_id
                vehicle_id=serializer.validated_data['scooter_id'],
                start_at=serializer.validated_data['start_datetime'],
                end_at=serializer.validated_data['end_datetime'],
                addon_ids=serializer.validated_data.get('add_on_ids'),
                payment_method=serializer.validated_data.get('payment_method', 'online_card'),
                delivery_address_text=serializer.validated_data.get('delivery_address'),
                delivery_lat=serializer.validated_data.get('delivery_latitude'),
                delivery_lng=serializer.validated_data.get('delivery_longitude'),
                currency=serializer.validated_data.get('currency', 'USD'),
                request_info={
                    'ip': request.META.get('REMOTE_ADDR'),
                    'user_agent': request.META.get('HTTP_USER_AGENT')
                }
            )
            # Audit log is handled by service or we can add extra info here
            return Response(self.get_serializer(booking).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
    queryset = User.objects.all().order_by('-date_joined', '-id')
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAdminUser]
