from rest_framework import serializers, viewsets, permissions
from .models import Booking, BookingAddon, BookingStatusHistory, AvailabilityBlock
from bali_rent.permissions import IsBookingOwnerOrAdmin
from django.utils.dateparse import parse_datetime

class BookingAddonSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingAddon
        fields = '__all__'

class AvailabilityBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilityBlock
        fields = '__all__'

class BookingSerializer(serializers.ModelSerializer):
    addons = BookingAddonSerializer(many=True, read_only=True)
    
    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ('public_number', 'user', 'status', 'total_usd')

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated, IsBookingOwnerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Booking.objects.all()
        return Booking.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        import uuid
        public_number = str(uuid.uuid4().hex[:8]).upper()
        serializer.save(user=self.request.user, public_number=public_number)

class AvailabilityBlockViewSet(viewsets.ModelViewSet):
    queryset = AvailabilityBlock.objects.select_related('vehicle', 'source_booking').order_by('start_at', 'id')
    serializer_class = AvailabilityBlockSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def get_queryset(self):
        queryset = super().get_queryset()
        vehicle_id = self.request.query_params.get('vehicle')
        start_at = parse_datetime(self.request.query_params.get('start_at', ''))
        end_at = parse_datetime(self.request.query_params.get('end_at', ''))

        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)
        if start_at:
            queryset = queryset.filter(end_at__gt=start_at)
        if end_at:
            queryset = queryset.filter(start_at__lt=end_at)
        return queryset
