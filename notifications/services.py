import logging
from django.conf import settings
from .models import Notification, NotificationTemplate
from users.models import UserDevice, User

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def create_notification(user, title, body, notification_type, data_json=None):
        notification = Notification.objects.create(
            user=user,
            title=title,
            body=body,
            type=notification_type,
            data_json=data_json
        )
        NotificationService.send_push(user, title, body, data_json)
        return notification

    @staticmethod
    def send_push(user, title, body, data=None):
        devices = UserDevice.objects.filter(user=user, is_active=True)
        if not devices.exists():
            logger.info(f"No active devices for user {user.email}")
            return

        # Safe stub for dev if Firebase not configured
        fcm_api_key = getattr(settings, 'FCM_SERVER_KEY', None)
        
        for device in devices:
            if not fcm_api_key:
                logger.info(f"[STUB] Sending push to {device.fcm_token}: {title} - {body}")
            else:
                # In a real implementation, call FCM API here
                logger.info(f"Sending real push to {device.fcm_token} (FCM implementation pending)")

    @staticmethod
    def send_to_all(title, body, notification_type, data_json=None):
        users = User.objects.filter(is_active=True)
        for user in users:
            NotificationService.create_notification(user, title, body, notification_type, data_json)

    @staticmethod
    def send_to_segment(segment, title, body, notification_type, data_json=None):
        # Example segment logic: role-based
        users = User.objects.filter(role=segment, is_active=True)
        for user in users:
            NotificationService.create_notification(user, title, body, notification_type, data_json)
