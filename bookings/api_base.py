from rest_framework import serializers, viewsets, permissions
from .models import Booking, BookingAddon, BookingStatusHistory, AvailabilityBlock
from bali_rent.permissions import IsBookingOwnerOrAdmin

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

class AvailabilityBlockViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AvailabilityBlock.objects.all()
    serializer_class = AvailabilityBlockSerializer
    permission_classes = [permissions.AllowAny]
