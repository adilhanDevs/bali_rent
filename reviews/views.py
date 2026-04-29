from django.db import models
from django.db.models import Avg, Count
from rest_framework import viewsets, permissions, status, response, decorators
from .models import Review
from .serializers import ReviewSerializer
from bali_rent.permissions import IsOwnerOrAdmin
from events.services import emit_event

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
        scooter_id = self.kwargs.get('scooter_id')
        if scooter_id:
            queryset = queryset.filter(scooter_id=scooter_id)
        
        if not self.request.user.is_staff:
            if self.request.user.is_authenticated:
                queryset = queryset.filter(
                    models.Q(status='approved') | models.Q(user=self.request.user)
                )
            else:
                queryset = queryset.filter(status='approved')
        
        return queryset

    def perform_create(self, serializer):
        review = serializer.save(user=self.request.user, status='pending')
        emit_event("review_created", {
            "user": self.request.user,
            "review_id": review.id,
            "rating": review.rating,
            "comment": review.comment,
            "scooter_id": review.scooter_id,
        })

    def update_scooter_stats(self, scooter):
        stats = Review.objects.filter(scooter=scooter, status='approved').aggregate(
            avg_rating=Avg('rating'),
            count=Count('id')
        )
        scooter.rating_avg = stats['avg_rating'] or 0.0
        scooter.reviews_count = stats['count'] or 0
        scooter.save()

class AdminReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all().order_by('-created_at')
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAdminUser]

    @decorators.action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        review = self.get_object()
        review.status = 'approved'
        review.save()
        
        # Update scooter stats
        self.update_scooter_stats(review.scooter)
        
        return response.Response({'status': 'approved'})

    @decorators.action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        review = self.get_object()
        review.status = 'rejected'
        review.save()
        
        # Update scooter stats
        self.update_scooter_stats(review.scooter)
        
        return response.Response({'status': 'rejected'})

    def update_scooter_stats(self, scooter):
        stats = Review.objects.filter(scooter=scooter, status='approved').aggregate(
            avg_rating=Avg('rating'),
            count=Count('id')
        )
        scooter.rating_avg = stats['avg_rating'] or 0.0
        scooter.reviews_count = stats['count'] or 0
        scooter.save()
