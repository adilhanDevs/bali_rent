import json
from decimal import Decimal, InvalidOperation

from django.db import transaction

from crm.models import CustomerInteraction, CustomerProfile, CustomerSegment


SEGMENT_NEW = "new"
SEGMENT_REGULAR = "regular"
SEGMENT_VIP = "vip"


def _to_decimal(value):
    if value in (None, ""):
        return Decimal("0.00")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def _profile_from_payload(payload):
    user = payload.get("user")
    user_id = getattr(user, "id", None) or payload.get("user_id")
    if not user_id:
        return None
    return CustomerProfile.objects.select_related("segment", "user").filter(user_id=user_id).first()


def _interaction_payload(interaction):
    if not interaction.description:
        return {}
    try:
        return json.loads(interaction.description)
    except json.JSONDecodeError:
        return {}


def get_customer_metrics(profile):
    bookings_count = 0
    total_spent = Decimal("0.00")

    interactions = profile.interactions.filter(interaction_type__in=["booking", "payment"])
    for interaction in interactions:
        payload = _interaction_payload(interaction)
        if interaction.interaction_type == "booking":
            bookings_count += 1
            total_spent += _to_decimal(payload.get("price"))
        elif interaction.interaction_type == "payment":
            total_spent += _to_decimal(payload.get("amount"))

    return {
        "bookings_count": bookings_count,
        "total_spent": total_spent,
    }


def _segment_for_total(total_spent):
    if total_spent > Decimal("1000"):
        return SEGMENT_VIP, "VIP"
    if total_spent > Decimal("100"):
        return SEGMENT_REGULAR, "Regular"
    return SEGMENT_NEW, "New"


def _ensure_segment(total_spent):
    code, default_name = _segment_for_total(total_spent)
    segment, _ = CustomerSegment.objects.get_or_create(
        code=code,
        defaults={"name": default_name, "discount_percent": Decimal("0.00")},
    )
    return segment


def _attach_metrics(profile):
    metrics = get_customer_metrics(profile)
    profile.bookings_count = metrics["bookings_count"]
    profile.total_spent = metrics["total_spent"]
    return profile


def _sync_segment(profile):
    metrics = get_customer_metrics(profile)
    segment = _ensure_segment(metrics["total_spent"])
    if profile.segment_id != segment.id:
        profile.segment = segment
        profile.save(update_fields=["segment", "updated_at"])
    return _attach_metrics(profile)


@transaction.atomic
def handle_booking_created(payload):
    profile = _profile_from_payload(payload)
    if profile is None:
        return None

    interaction_payload = {
        "booking_id": payload.get("booking_id"),
        "price": str(_to_decimal(payload.get("price") or payload.get("total_usd"))),
        "vehicle_sku": payload.get("vehicle_sku"),
    }
    CustomerInteraction.objects.create(
        customer=profile,
        interaction_type="booking",
        description=json.dumps(interaction_payload, sort_keys=True),
    )
    return _sync_segment(profile)


@transaction.atomic
def handle_payment_completed(payload):
    profile = _profile_from_payload(payload)
    if profile is None:
        return None

    interaction_payload = {
        "payment_id": payload.get("payment_id"),
        "booking_id": payload.get("booking_id"),
        "amount": str(_to_decimal(payload.get("amount"))),
        "currency": payload.get("currency", "USD"),
    }
    CustomerInteraction.objects.create(
        customer=profile,
        interaction_type="payment",
        description=json.dumps(interaction_payload, sort_keys=True),
    )
    return _sync_segment(profile)
