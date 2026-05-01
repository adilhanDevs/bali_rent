from decimal import Decimal, InvalidOperation, ROUND_DOWN

from django.core.cache import cache
from django.db import transaction

from loyalty.models import (
    CustomerLoyaltyAccount,
    LoyaltyProgram,
    LoyaltyTier,
    LoyaltyTransaction,
)


DEFAULT_PROGRAM_NAME = "Default Loyalty Program"
DEFAULT_EVENT_DEDUPE_TIMEOUT = 60 * 60 * 24

DEFAULT_TIERS = (
    ("Bronze", 0, "0.00"),
    ("Silver", 100, "5.00"),
    ("Gold", 500, "10.00"),
)


def _resolve_user(payload):
    user = payload.get("user")
    if user is not None and hasattr(user, "pk"):
        return user
    return None


def _resolve_points(amount):
    if amount in (None, ""):
        return 0
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        return 0
    if value <= 0:
        return 0
    return int(value.quantize(Decimal("1"), rounding=ROUND_DOWN))


def _event_key(payload):
    payment_id = payload.get("payment_id")
    if payment_id not in (None, ""):
        return f"loyalty-payment-completed:{payment_id}"

    booking_id = payload.get("booking_id")
    user = _resolve_user(payload)
    amount = payload.get("amount")
    if booking_id not in (None, "") and user is not None:
        return f"loyalty-payment-completed:{user.pk}:{booking_id}:{amount}"

    return None


def _ensure_program():
    program, _ = LoyaltyProgram.objects.get_or_create(
        name=DEFAULT_PROGRAM_NAME,
        defaults={"is_active": True},
    )
    if not program.is_active:
        program.is_active = True
        program.save(update_fields=["is_active"])
    return program


def _ensure_tiers(program):
    for name, min_points, discount_percent in DEFAULT_TIERS:
        LoyaltyTier.objects.get_or_create(
            program=program,
            name=name,
            defaults={
                "min_points": min_points,
                "discount_percent": discount_percent,
            },
        )


def _get_or_create_account(user):
    account = (
        CustomerLoyaltyAccount.objects.select_related("program", "tier")
        .filter(customer=user)
        .order_by("id")
        .first()
    )
    if account is not None:
        _ensure_tiers(account.program)
        return account

    program = _ensure_program()
    _ensure_tiers(program)
    account, _ = CustomerLoyaltyAccount.objects.get_or_create(
        customer=user,
        program=program,
        defaults={"points": 0},
    )
    return account


@transaction.atomic
def handle_payment_completed(payload):
    user = _resolve_user(payload)
    if user is None:
        return None

    points = _resolve_points(payload.get("amount"))
    if points <= 0:
        return None

    event_key = _event_key(payload)
    if event_key and not cache.add(event_key, True, timeout=DEFAULT_EVENT_DEDUPE_TIMEOUT):
        return None

    account = _get_or_create_account(user)
    loyalty_transaction = LoyaltyTransaction.objects.create(
        account=account,
        points=points,
        type=LoyaltyTransaction.TYPE_EARN,
    )
    account.refresh_from_db()
    return loyalty_transaction
