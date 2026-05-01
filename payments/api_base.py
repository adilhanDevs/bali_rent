from rest_framework import serializers, viewsets, permissions
from .models import Payment
from bali_rent.permissions import IsBookingOwnerOrAdmin
from audit.mixins import AuditMixin

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class PaymentViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = Payment.objects.all().select_related('booking', 'booking__user')
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsBookingOwnerOrAdmin]

    def get_queryset(self):
        queryset = Payment.objects.select_related('booking', 'booking__user').order_by('-created_at', '-id')
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(booking__user=self.request.user)
