from django.db.models import Avg
from rest_framework import serializers, viewsets, permissions, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Review
from bookings.models import Booking
from catalog.models import Vehicle
from bali_rent.permissions import IsOwnerOrAdmin

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'booking', 'vehicle', 'user', 'user_name', 'rating', 'text', 'status', 'created_at']
        read_only_fields = ['id', 'user', 'status', 'created_at']

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate(self, data):
        user = self.context['request'].user
        booking = data.get('booking')
        vehicle = data.get('vehicle')

        if booking.user != user:
            raise serializers.ValidationError("You can only review your own bookings.")
        
        if booking.vehicle != vehicle:
            raise serializers.ValidationError("Booking does not match the vehicle.")

        if booking.status != 'completed':
            raise serializers.ValidationError("You can only review completed bookings.")

        if Review.objects.filter(booking=booking).exists():
            raise serializers.ValidationError("You have already reviewed this booking.")

        return data

class ReviewService:
    @staticmethod
    def update_vehicle_stats(vehicle):
        stats = Review.objects.filter(vehicle=vehicle, status='published').aggregate(
            avg_rating=Avg('rating'),
            count=models.Count('id')
        )
        vehicle.rating_avg = stats['avg_rating'] or 0.0
        vehicle.reviews_count = stats['count'] or 0
        vehicle.save()

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        if self.action in ['create']:
            return [permissions.IsAuthenticated()]
        return [IsOwnerOrAdmin()]

    def get_queryset(self):
        queryset = Review.objects.all()
        scooter_id = self.request.query_params.get('scooter_id')
        if scooter_id:
            queryset = queryset.filter(vehicle_id=scooter_id)
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(status='published') | queryset.filter(user=self.request.user.id if self.request.user.is_authenticated else None)
        
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status='pending')

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        review = self.get_object()
        review.status = 'published'
        review.save()
        
        # Update vehicle stats
        from django.db import models
        stats = Review.objects.filter(vehicle=review.vehicle, status='published').aggregate(
            avg_rating=models.Avg('rating'),
            count=models.Count('id')
        )
        review.vehicle.rating_avg = stats['avg_rating'] or 0.0
        review.vehicle.reviews_count = stats['count'] or 0
        review.vehicle.save()
        
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        review = self.get_object()
        review.status = 'hidden'
        review.save()
        return Response({'status': 'rejected'})

class AdminReviewListView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        reviews = Review.objects.all().order_by('-created_at')
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)
