from rest_framework import serializers
from .models import AuditLog, AdminLoginLog, WebhookProcessingLog
from .services import redact_sensitive_data
from django.contrib.contenttypes.models import ContentType

class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ['app_label', 'model']

class AuditLogSerializer(serializers.ModelSerializer):
    content_type = ContentTypeSerializer(read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    before_json = serializers.SerializerMethodField()
    after_json = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_email', 'content_type', 'object_id',
            'action', 'before_json', 'after_json', 'ip_address',
            'user_agent', 'created_at'
        ]

    def _filter_sensitive(self, data):
        return redact_sensitive_data(data)

    def get_before_json(self, obj):
        return self._filter_sensitive(obj.before_json)

    def get_after_json(self, obj):
        return self._filter_sensitive(obj.after_json)

class AdminLoginLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = AdminLoginLog
        fields = ['id', 'user', 'user_email', 'ip_address', 'user_agent', 'is_success', 'created_at']

class WebhookProcessingLogSerializer(serializers.ModelSerializer):
    payload_json = serializers.SerializerMethodField()

    class Meta:
        model = WebhookProcessingLog
        fields = '__all__'

    def get_payload_json(self, obj):
        return redact_sensitive_data(obj.payload_json)
