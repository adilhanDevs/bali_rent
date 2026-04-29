from decimal import Decimal

import pytest

from crm.models import CustomerInteraction, CustomerProfile, CustomerSegment
from crm.services.events_handlers import get_customer_metrics
from events.services import emit_event


pytestmark = pytest.mark.django_db


@pytest.fixture
def customer_profile(user):
    return CustomerProfile.objects.create(user=user)


def test_booking_created_increases_bookings_count(customer_profile, user):
    emit_event(
        "booking_created",
        {
            "user": user,
            "booking_id": 101,
        },
    )

    customer_profile.refresh_from_db()
    metrics = get_customer_metrics(customer_profile)
    assert metrics["bookings_count"] == 1
    assert metrics["total_spent"] == Decimal("0.00")
    assert CustomerInteraction.objects.filter(customer=customer_profile, interaction_type="booking").count() == 1


def test_booking_created_with_price_updates_total_spent_and_regular_segment(customer_profile, user):
    emit_event(
        "booking_created",
        {
            "user": user,
            "booking_id": 102,
            "price": "150.00",
        },
    )

    customer_profile.refresh_from_db()
    metrics = get_customer_metrics(customer_profile)
    assert metrics["bookings_count"] == 1
    assert metrics["total_spent"] == Decimal("150.00")
    assert customer_profile.segment.code == "regular"


def test_payment_completed_increases_total_spent(customer_profile, user):
    emit_event(
        "payment_completed",
        {
            "user": user,
            "payment_id": 501,
            "amount": "75.50",
        },
    )

    customer_profile.refresh_from_db()
    metrics = get_customer_metrics(customer_profile)
    assert metrics["bookings_count"] == 0
    assert metrics["total_spent"] == Decimal("75.50")


def test_segmentation_switches_to_vip_after_total_exceeds_threshold(customer_profile, user):
    emit_event(
        "booking_created",
        {
            "user": user,
            "booking_id": 201,
            "price": "300.00",
        },
    )
    emit_event(
        "payment_completed",
        {
            "user": user,
            "payment_id": 801,
            "amount": "800.01",
        },
    )

    customer_profile.refresh_from_db()
    metrics = get_customer_metrics(customer_profile)
    assert metrics["total_spent"] == Decimal("1100.01")
    assert customer_profile.segment.code == "vip"


def test_low_spend_profile_gets_new_segment(customer_profile, user):
    emit_event(
        "payment_completed",
        {
            "user": user,
            "payment_id": 701,
            "amount": "50.00",
        },
    )

    customer_profile.refresh_from_db()
    assert customer_profile.segment.code == "new"
    assert CustomerSegment.objects.filter(code="new").exists()


def test_missing_customer_profile_does_not_break_emit_event(user):
    event = emit_event(
        "booking_created",
        {
            "user": user,
            "booking_id": 999,
            "price": "120.00",
        },
    )

    assert event.event_name == "booking_created"
    assert CustomerInteraction.objects.count() == 0
