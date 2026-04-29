from django.utils import timezone
from rest_framework import decorators, permissions, response, viewsets, status

from .models import DocumentVerification, UserDocument
from .serializers import DocumentReviewSerializer, UserDocumentAdminSerializer, UserDocumentSerializer
from audit.mixins import AuditMixin


class IsDocumentAdminOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or user.role in {'admin', 'manager'}))

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class UserDocumentViewSet(AuditMixin, viewsets.ModelViewSet):
    serializer_class = UserDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return UserDocument.objects.select_related('user', 'reviewed_by').prefetch_related('verifications')
        return (
            UserDocument.objects.filter(user=self.request.user)
            .select_related('user', 'reviewed_by')
            .prefetch_related('verifications')
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status='pending', rejection_reason='')
        super().perform_create(serializer)

    @decorators.action(detail=False, methods=['get'], url_path='my')
    def my(self, request):
        queryset = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return response.Response(serializer.data)


class AdminDocumentViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = UserDocument.objects.select_related('user', 'reviewed_by').prefetch_related('verifications')
    serializer_class = UserDocumentAdminSerializer
    permission_classes = [IsDocumentAdminOrManager]

    @decorators.action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        document = self.get_object()
        document.status = 'approved'
        document.rejection_reason = ''
        document.reviewed_by = request.user
        document.reviewed_at = timezone.now()
        document.save()
        
        DocumentVerification.objects.create(
            document=document,
            verified_by=request.user,
            status='approved',
        )
        
        self._log_audit(document, 'approve', after_dict={'status': 'approved'})
        return response.Response({'status': 'approved'})

    @decorators.action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        serializer = DocumentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document = self.get_object()
        document.status = 'rejected'
        document.rejection_reason = serializer.validated_data.get('rejection_reason', '')
        document.reviewed_by = request.user
        document.reviewed_at = timezone.now()
        document.save()
        
        DocumentVerification.objects.create(
            document=document,
            verified_by=request.user,
            status='rejected',
        )
        
        self._log_audit(document, 'reject', after_dict={'status': 'rejected', 'reason': document.rejection_reason})
        return response.Response({'status': 'rejected'})
