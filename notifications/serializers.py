from rest_framework import serializers
from .models import Notification
from users.models import UserDevice


class NotificationSerializer(serializers.ModelSerializer):
    message = serializers.CharField(source='body', read_only=True)
    data = serializers.JSONField(source='data_json', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'body',
            'message',
            'type',
            'data_json',
            'data',
            'is_read',
            'read_at',
            'sent_at',
            'created_at',
        ]
        read_only_fields = fields


class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = ['fcm_token', 'platform', 'device_id', 'app_version']
        extra_kwargs = {
            'fcm_token': {'validators': []},
        }


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
    body = serializers.CharField(required=False)
    message = serializers.CharField(required=False, write_only=True)
    type = serializers.CharField(max_length=50, default='admin_broadcast')
    data_json = serializers.JSONField(required=False)
    data = serializers.JSONField(required=False, write_only=True)

    def validate(self, attrs):
        body = attrs.get('body') or attrs.get('message')
        if not body:
            raise serializers.ValidationError({'body': 'This field is required.'})

        attrs['body'] = body
        if 'data_json' not in attrs and 'data' in attrs:
            attrs['data_json'] = attrs['data']

        if attrs['target'] == 'user' and not attrs.get('user_id'):
            raise serializers.ValidationError({'user_id': 'This field is required for user target.'})
        if attrs['target'] == 'segment' and not attrs.get('segment'):
            raise serializers.ValidationError({'segment': 'This field is required for segment target.'})

        return attrs
