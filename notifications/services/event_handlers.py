import json

from notifications.services import NotificationService


def _resolve_user(payload):
    user = payload.get("user")
    if user is not None and hasattr(user, "pk"):
        return user
    return None


def _payload_snapshot(payload):
    safe_payload = dict(payload or {})
    user = safe_payload.pop("user", None)
    if user is not None and hasattr(user, "pk"):
        safe_payload["user_id"] = user.pk
    return safe_payload


def _event_key(prefix, payload, id_keys):
    for key in id_keys:
        value = payload.get(key)
        if value not in (None, ""):
            return f"{prefix}:{value}"

    snapshot = json.dumps(_payload_snapshot(payload), sort_keys=True, default=str)
    return f"{prefix}:{snapshot}"


def _dispatch_if_user(*, payload, title, body, notification_type, event_key):
    user = _resolve_user(payload)
    if user is None:
        return None

    return NotificationService.dispatch_notification(
        user=user,
        title=title,
        body=body,
        notification_type=notification_type,
        data_json=_payload_snapshot(payload),
        event_key=event_key,
    )


def handle_booking_created(payload):
    return _dispatch_if_user(
        payload=payload,
        title="Бронь создана",
        body="Ваша бронь успешно создана.",
        notification_type="booking_created",
        event_key=_event_key("event-booking-created", payload, ["booking_id"]),
    )


def handle_payment_completed(payload):
    return _dispatch_if_user(
        payload=payload,
        title="Оплата прошла",
        body="Мы получили вашу оплату.",
        notification_type="payment_completed",
        event_key=_event_key("event-payment-completed", payload, ["payment_id", "booking_id"]),
    )


def handle_ticket_created(payload):
    return _dispatch_if_user(
        payload=payload,
        title="Тикет создан",
        body="Ваш тикет поддержки создан.",
        notification_type="ticket_created",
        event_key=_event_key("event-ticket-created", payload, ["ticket_id"]),
    )


def handle_message_sent(payload):
    return _dispatch_if_user(
        payload=payload,
        title="Новое сообщение",
        body="У вас появилось новое сообщение.",
        notification_type="message_sent",
        event_key=_event_key("event-message-sent", payload, ["message_id", "thread_id"]),
    )
