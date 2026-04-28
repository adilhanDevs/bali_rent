from rest_framework import serializers
from .models import Payment
from bookings.models import Booking

class PaymentCreateSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    provider = serializers.CharField(max_length=50, default='stripe')

    def validate_booking_id(self, value):
        try:
            booking = Booking.objects.get(id=value)
        except Booking.DoesNotExist:
            raise serializers.ValidationError("Booking not found")
        
        if booking.user != self.context['request'].user:
            raise serializers.ValidationError("You don't own this booking")
        
        if booking.status in ['paid', 'completed', 'cancelled']:
            raise serializers.ValidationError(f"Booking is in {booking.status} status and cannot be paid")
        
        return value

class PaymentResponseSerializer(serializers.ModelSerializer):
    payment_id = serializers.IntegerField(source='id')
    amount = serializers.DecimalField(source='amount_usd', max_digits=10, decimal_places=2)

    class Meta:
        model = Payment
        fields = ['payment_id', 'provider', 'status', 'payment_url', 'amount', 'currency']
