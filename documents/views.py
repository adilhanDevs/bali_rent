from django.utils import timezone
from rest_framework import viewsets, permissions, status, response, decorators
from .models import UserDocument
from .serializers import UserDocumentSerializer, UserDocumentAdminSerializer, DocumentReviewSerializer
from bali_rent.permissions import IsOwnerOrAdmin

class UserDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = UserDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # User can only see own documents. Staff can see all via this viewset too if we want, 
        # but prompt says "User can upload and view own documents. User cannot see other users' documents."
        if self.request.user.is_staff:
            return UserDocument.objects.all()
        return UserDocument.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Set status to pending on upload
        serializer.save(user=self.request.user, status='pending')

class AdminDocumentViewSet(viewsets.ModelViewSet):
    queryset = UserDocument.objects.all()
    serializer_class = UserDocumentAdminSerializer
    permission_classes = [permissions.IsAdminUser]

    @decorators.action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        doc = self.get_object()
        doc.status = 'approved'
        doc.reviewed_by = request.user
        doc.reviewed_at = timezone.now()
        doc.save()
        return response.Response({'status': 'approved'})

    @decorators.action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        serializer = DocumentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = self.get_object()
        doc.status = 'rejected'
        doc.rejection_reason = serializer.validated_data.get('rejection_reason', '')
        doc.reviewed_by = request.user
        doc.reviewed_at = timezone.now()
        doc.save()
        return response.Response({'status': 'rejected'})
