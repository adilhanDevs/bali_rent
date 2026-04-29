try:
    from celery import shared_task
except ImportError:  # pragma: no cover - optional dependency
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def create_notification_task(self, user_id, title, body, notification_type, data_json=None, event_key=None):
    from .services import NotificationService
    try:
        NotificationService.create_notification_by_user_id(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            data_json=data_json,
            event_key=event_key,
        )
    except Exception as exc:
        # Retry for any unexpected exceptions (network, DB locks, etc.)
        raise self.retry(exc=exc)
