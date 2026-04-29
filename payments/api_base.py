from rest_framework import serializers, viewsets, permissions
from .models import Payment
from bali_rent.permissions import IsBookingOwnerOrAdmin
from audit.mixins import AuditMixin

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class PaymentViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = Payment.objects.all().order_by('-created_at', '-id')
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsBookingOwnerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(booking__user=self.request.user)
