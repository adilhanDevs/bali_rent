from django.utils import timezone
from rest_framework import viewsets, permissions, status, response, decorators
from .models import UserDocument
from .serializers import UserDocumentSerializer, UserDocumentAdminSerializer, DocumentReviewSerializer
from bali_rent.permissions import IsOwnerOrAdmin
from notifications.services import NotificationService

class UserDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = UserDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # User can only see own documents. Staff can see all via this viewset too if we want, 
        # but prompt says "User can upload and view own documents. User cannot see other users' documents."
        if self.request.user.is_staff:
            return UserDocument.objects.all().order_by('-created_at')
        return UserDocument.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # Set status to pending on upload
        document = serializer.save(user=self.request.user, status='pending')
        NotificationService.create_notification(
            self.request.user,
            'Document uploaded',
            f'Your {document.document_type} was uploaded and is pending review.',
            'document_uploaded',
            {'document_id': document.id, 'status': document.status},
        )

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
        NotificationService.create_notification(
            doc.user,
            'Document approved',
            f'Your {doc.document_type} was approved.',
            'document_approved',
            {'document_id': doc.id, 'status': doc.status},
        )
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
        NotificationService.create_notification(
            doc.user,
            'Document rejected',
            f'Your {doc.document_type} was rejected. {doc.rejection_reason}'.strip(),
            'document_rejected',
            {'document_id': doc.id, 'status': doc.status, 'rejection_reason': doc.rejection_reason},
        )
        return response.Response({'status': 'rejected'})
