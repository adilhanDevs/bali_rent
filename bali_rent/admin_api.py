from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from catalog.models import Vehicle, VehicleImage
from bookings.models import Booking
from users.models import User
from catalog.serializers import ScooterDetailSerializer, ScooterImageSerializer
from bookings.serializers import BookingSerializer
from users.serializers import UserSerializer
from django.utils import timezone

class AdminScooterViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = ScooterDetailSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=True, methods=['post'])
    def images(self, request, pk=None):
        vehicle = self.get_object()
        serializer = ScooterImageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(vehicle=vehicle)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminScooterImageViewSet(viewsets.GenericViewSet):
    queryset = VehicleImage.objects.all()
    permission_classes = [permissions.IsAdminUser]

    def destroy(self, request, pk=None):
        image = self.get_object()
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdminBookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'vehicle', 'user']
    ordering_fields = ['created_at', 'start_at']

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
        booking.status = new_status
        booking.save()
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
        
        booking.status = 'cancelled'
        booking.save()
        booking.availability_blocks.all().delete()
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

class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
