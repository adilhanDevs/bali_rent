from rest_framework import viewsets, permissions
from .models import AuditLog, AdminLoginLog, WebhookProcessingLog
from .serializers import AuditLogSerializer, AdminLoginLogSerializer, WebhookProcessingLogSerializer

class AdminAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['user', 'action', 'content_type', 'object_id']
    ordering_fields = ['created_at']

class AdminSecurityLoginLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AdminLoginLog.objects.all()
    serializer_class = AdminLoginLogSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['user', 'is_success', 'ip_address']
    ordering_fields = ['created_at']

class AdminSecurityWebhookLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WebhookProcessingLog.objects.all()
    serializer_class = WebhookProcessingLogSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['provider', 'status', 'event_type']
    ordering_fields = ['created_at', 'processing_time_ms']
