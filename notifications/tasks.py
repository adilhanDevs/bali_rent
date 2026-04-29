try:
    from celery import shared_task
except ImportError:  # pragma: no cover - optional dependency
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


@shared_task
def create_notification_task(user_id, title, body, notification_type, data_json=None, event_key=None):
    from .services import NotificationService

    NotificationService.create_notification_by_user_id(
        user_id=user_id,
        title=title,
        body=body,
        notification_type=notification_type,
        data_json=data_json,
        event_key=event_key,
    )
