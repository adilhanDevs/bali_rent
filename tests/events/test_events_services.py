from copy import deepcopy

import pytest

from analytics.models import AnalyticsEvent
from events.services import EventService, emit_event


pytestmark = pytest.mark.django_db


def test_emit_event_persists_supported_event_with_metadata(user):
    event = emit_event(
        "booking_created",
        {
            "user": user,
            "session_id": "session-1",
            "device_id": "device-1",
            "ip_address": "127.0.0.1",
            "user_agent": "pytest",
            "booking_id": 123,
            "total_usd": 150.5,
        },
    )

    assert event.event_name == "booking_created"
    assert event.user == user
    assert event.session_id == "session-1"
    assert event.device_id == "device-1"
    assert event.ip_address == "127.0.0.1"
    assert event.user_agent == "pytest"
    assert event.payload == {"booking_id": 123, "total_usd": 150.5}


def test_emit_event_supports_all_declared_events():
    event_names = [
        "booking_created",
        "payment_completed",
        "ticket_created",
        "message_sent",
        "review_created",
    ]

    for index, event_name in enumerate(event_names, start=1):
        emit_event(event_name, {"sequence": index})

    assert list(AnalyticsEvent.objects.order_by("id").values_list("event_name", flat=True)) == event_names


def test_emit_event_rejects_unknown_event():
    with pytest.raises(ValueError, match="Unsupported event"):
        emit_event("unknown_event", {"foo": "bar"})

    assert AnalyticsEvent.objects.count() == 0


def test_emit_event_rejects_non_dict_payload():
    with pytest.raises(ValueError, match="dictionary"):
        emit_event("payment_completed", ["not", "a", "dict"])

    assert AnalyticsEvent.objects.count() == 0


def test_emit_event_rejects_invalid_user_payload():
    with pytest.raises(ValueError, match="Django user instance"):
        emit_event("review_created", {"user": 123, "review_id": 9})

    assert AnalyticsEvent.objects.count() == 0


def test_emit_event_defaults_to_empty_payload():
    event = emit_event("message_sent")

    assert event.payload == {}
    assert event.event_name == "message_sent"


def test_emit_event_does_not_mutate_input_payload(user):
    payload = {
        "user": user,
        "session_id": "s-1",
        "booking_id": 55,
        "nested": {"status": "created"},
    }
    original = deepcopy(payload)

    emit_event("booking_created", payload)

    assert payload["user"] == original["user"]
    assert payload["session_id"] == original["session_id"]
    assert payload["nested"] == original["nested"]


def test_event_service_class_method_matches_helper(user):
    event = EventService.emit_event(
        "ticket_created",
        {
            "user": user,
            "ticket_id": 77,
            "channel": "app",
        },
    )

    saved = AnalyticsEvent.objects.get(pk=event.pk)
    assert saved.event_name == "ticket_created"
    assert saved.payload == {"ticket_id": 77, "channel": "app"}
