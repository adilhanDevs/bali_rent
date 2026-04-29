import logging
from django.db import IntegrityError, transaction
from django.conf import settings
from django.utils import timezone

from .models import Notification, NotificationLog, NotificationTemplate
from users.models import UserDevice, User

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def create_notification(user, title, body, notification_type, data_json=None, event_key=None):
        existing = None
        if event_key:
            existing = NotificationLog.objects.select_related('notification').filter(event_key=event_key).first()
            if existing and existing.notification:
                return existing.notification

        try:
            with transaction.atomic():
                notification = Notification.objects.create(
                    user=user,
                    title=title,
                    body=body,
                    type=notification_type,
                    data_json=data_json,
                    sent_at=timezone.now(),
                )
                NotificationLog.objects.create(
                    notification=notification,
                    user=user,
                    event_type=notification_type,
                    event_key=event_key,
                    channel='in_app',
                    status='sent',
                    payload_json=data_json,
                )
        except IntegrityError:
            if event_key:
                existing = NotificationLog.objects.select_related('notification').get(event_key=event_key)
                return existing.notification
            raise

        NotificationService.send_push(user, title, body, data_json)
        return notification

    @staticmethod
    def create_notification_by_user_id(user_id, title, body, notification_type, data_json=None, event_key=None):
        user = User.objects.get(pk=user_id)
        return NotificationService.create_notification(
            user=user,
            title=title,
            body=body,
            notification_type=notification_type,
            data_json=data_json,
            event_key=event_key,
        )

    @staticmethod
    def dispatch_notification(user, title, body, notification_type, data_json=None, event_key=None):
        if getattr(settings, 'NOTIFICATIONS_USE_CELERY', False):
            try:
                from .tasks import create_notification_task

                create_notification_task.delay(
                    user.id,
                    title,
                    body,
                    notification_type,
                    data_json or {},
                    event_key,
                )
                return None
            except Exception:
                logger.exception('Celery dispatch failed, falling back to sync notification creation')

        return NotificationService.create_notification(
            user=user,
            title=title,
            body=body,
            notification_type=notification_type,
            data_json=data_json,
            event_key=event_key,
        )

    @staticmethod
    def mark_as_read(notification):
        notification.mark_as_read()
        return notification

    @staticmethod
    def notify_booking_created(booking):
        payload = {
            'booking_id': booking.id,
            'public_number': booking.public_number,
            'status': booking.status,
            'total_usd': str(booking.total_usd),
        }
        return NotificationService.dispatch_notification(
            user=booking.user,
            title='Booking created',
            body=f'Your booking {booking.public_number} was created successfully.',
            notification_type='booking_created',
            data_json=payload,
            event_key=f'booking-created:{booking.id}',
        )

    @staticmethod
    def notify_booking_confirmed(booking):
        payload = {
            'booking_id': booking.id,
            'public_number': booking.public_number,
            'status': booking.status,
        }
        return NotificationService.dispatch_notification(
            user=booking.user,
            title='Booking confirmed',
            body=f'Your booking {booking.public_number} is now confirmed.',
            notification_type='booking_confirmed',
            data_json=payload,
            event_key=f'booking-confirmed:{booking.id}',
        )

    @staticmethod
    def notify_payment_success(payment):
        payload = {
            'payment_id': payment.id,
            'booking_id': payment.booking_id,
            'public_number': payment.booking.public_number,
            'amount_usd': str(payment.amount_usd),
            'status': payment.status,
        }
        return NotificationService.dispatch_notification(
            user=payment.booking.user,
            title='Payment successful',
            body=f'Payment for booking {payment.booking.public_number} was received.',
            notification_type='payment_success',
            data_json=payload,
            event_key=f'payment-success:{payment.id}',
        )

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
