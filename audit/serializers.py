from rest_framework import serializers
from .models import AuditLog, AdminLoginLog, WebhookProcessingLog
from django.contrib.contenttypes.models import ContentType

class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ['app_label', 'model']

class AuditLogSerializer(serializers.ModelSerializer):
    content_type = ContentTypeSerializer(read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_email', 'content_type', 'object_id',
            'action', 'before_json', 'after_json', 'ip_address',
            'user_agent', 'created_at'
        ]

class AdminLoginLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = AdminLoginLog
        fields = ['id', 'user', 'user_email', 'ip_address', 'user_agent', 'is_success', 'created_at']

class WebhookProcessingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookProcessingLog
        fields = '__all__'
