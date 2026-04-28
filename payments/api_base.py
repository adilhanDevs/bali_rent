from rest_framework import serializers, viewsets, permissions
from .models import Payment
from bali_rent.permissions import IsBookingOwnerOrAdmin

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsBookingOwnerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(booking__user=self.request.user)
