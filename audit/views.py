from rest_framework import viewsets, permissions
from .models import AuditLog, AdminLoginLog, WebhookProcessingLog
from .serializers import AuditLogSerializer, AdminLoginLogSerializer, WebhookProcessingLogSerializer

class AdminAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]

class AdminSecurityLoginLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AdminLoginLog.objects.all()
    serializer_class = AdminLoginLogSerializer
    permission_classes = [permissions.IsAdminUser]

class AdminSecurityWebhookLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WebhookProcessingLog.objects.all()
    serializer_class = WebhookProcessingLogSerializer
    permission_classes = [permissions.IsAdminUser]
