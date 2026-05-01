import pytest

from events.services import emit_event
from notifications.models import Notification


pytestmark = pytest.mark.django_db


def test_booking_created_creates_notification(user):
    emit_event(
        "booking_created",
        {
            "user": user,
            "booking_id": 1001,
            "price": "120.00",
        },
    )

    notification = Notification.objects.get(type="booking_created")
    assert notification.user == user
    assert notification.title == "Бронь создана"


def test_payment_completed_creates_notification(user):
    emit_event(
        "payment_completed",
        {
            "user": user,
            "payment_id": 2001,
            "amount": "75.00",
        },
    )

    notification = Notification.objects.get(type="payment_completed")
    assert notification.user == user
    assert notification.title == "Оплата прошла"


def test_ticket_created_creates_notification(user):
    emit_event(
        "ticket_created",
        {
            "user": user,
            "ticket_id": 3001,
            "channel": "app",
        },
    )

    notification = Notification.objects.get(type="ticket_created")
    assert notification.user == user
    assert notification.title == "Тикет создан"


def test_message_sent_creates_notification(user):
    emit_event(
        "message_sent",
        {
            "user": user,
            "message_id": 4001,
            "thread_id": 88,
        },
    )

    notification = Notification.objects.get(type="message_sent")
    assert notification.user == user
    assert notification.title == "Новое сообщение"


def test_duplicate_events_do_not_create_duplicate_notifications(user):
    payload = {
        "user": user,
        "booking_id": 5001,
        "price": "99.00",
    }

    emit_event("booking_created", payload)
    emit_event("booking_created", payload)

    assert Notification.objects.filter(type="booking_created", user=user).count() == 1


def test_missing_user_in_payload_is_safe_and_creates_no_notification():
    emit_event(
        "ticket_created",
        {
            "ticket_id": 6001,
        },
    )

    assert Notification.objects.count() == 0
