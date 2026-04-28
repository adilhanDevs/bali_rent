from rest_framework import serializers
from .models import Notification
from users.models import UserDevice

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'body', 'type', 'data_json', 'is_read', 'sent_at', 'created_at']
        read_only_fields = ['id', 'title', 'body', 'type', 'data_json', 'sent_at', 'created_at']

class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = ['fcm_token', 'platform', 'device_id', 'app_version']

class AdminNotificationSendSerializer(serializers.Serializer):
    TARGET_CHOICES = (
        ('user', 'Specific User'),
        ('all', 'All Users'),
        ('segment', 'Segment'),
    )
    target = serializers.ChoiceField(choices=TARGET_CHOICES)
    user_id = serializers.IntegerField(required=False)
    segment = serializers.CharField(required=False)
    title = serializers.CharField(max_length=255)
    body = serializers.CharField()
    type = serializers.CharField(max_length=50, default='admin_broadcast')
    data_json = serializers.JSONField(required=False)
