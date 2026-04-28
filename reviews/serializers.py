from rest_framework import serializers
from .models import Review
from bookings.models import Booking

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    scooter_title = serializers.CharField(source='scooter.title', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'user', 'user_name', 'scooter', 'scooter_title', 
            'booking', 'rating', 'comment', 'status', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'status', 'created_at', 'updated_at']

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate(self, data):
        user = self.context['request'].user
        booking = data.get('booking')
        scooter = data.get('scooter')

        if booking:
            if booking.user != user:
                raise serializers.ValidationError("You can only review your own bookings.")
            if booking.vehicle != scooter:
                raise serializers.ValidationError("Booking does not match the selected scooter.")
            if booking.status != 'completed':
                raise serializers.ValidationError("You can only review completed bookings.")
            
            # One review per booking
            if Review.objects.filter(booking=booking).exclude(id=self.instance.id if self.instance else None).exists():
                raise serializers.ValidationError("You have already reviewed this booking.")
        else:
            if not self.instance:
                raise serializers.ValidationError("Booking is required to create a review.")

        return data
