from django.core.cache import cache
import pytest

from events.services import emit_event
from loyalty.models import (
    CustomerLoyaltyAccount,
    LoyaltyProgram,
    LoyaltyTier,
    LoyaltyTransaction,
)


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_loyalty_cache():
    cache.clear()


def test_payment_completed_awards_points(user):
    emit_event(
        "payment_completed",
        {
            "user": user,
            "payment_id": 1001,
            "amount": "120.00",
        },
    )

    account = CustomerLoyaltyAccount.objects.get(customer=user)
    assert account.points == 120


def test_payment_completed_updates_level_to_gold(user):
    emit_event(
        "payment_completed",
        {
            "user": user,
            "payment_id": 1002,
            "amount": "550.00",
        },
    )

    account = CustomerLoyaltyAccount.objects.select_related("tier").get(customer=user)
    assert account.tier is not None
    assert account.tier.name == "Gold"


def test_account_is_created_automatically(user):
    assert CustomerLoyaltyAccount.objects.filter(customer=user).exists() is False

    emit_event(
        "payment_completed",
        {
            "user": user,
            "payment_id": 1003,
            "amount": "25.00",
        },
    )

    account = CustomerLoyaltyAccount.objects.get(customer=user)
    assert account.program.name == "Default Loyalty Program"


def test_transaction_is_created_for_earn_event(user):
    emit_event(
        "payment_completed",
        {
            "user": user,
            "payment_id": 1004,
            "amount": "88.00",
        },
    )

    loyalty_transaction = LoyaltyTransaction.objects.get(account__customer=user)
    assert loyalty_transaction.type == LoyaltyTransaction.TYPE_EARN
    assert loyalty_transaction.points == 88


def test_duplicate_event_does_not_double_points(user):
    payload = {
        "user": user,
        "payment_id": 1005,
        "amount": "200.00",
    }

    emit_event("payment_completed", payload)
    emit_event("payment_completed", payload)

    account = CustomerLoyaltyAccount.objects.get(customer=user)
    assert account.points == 200
    assert LoyaltyTransaction.objects.filter(account=account).count() == 1


def test_missing_user_or_non_positive_amount_is_ignored(user):
    emit_event(
        "payment_completed",
        {
            "payment_id": 1006,
            "amount": "50.00",
        },
    )
    emit_event(
        "payment_completed",
        {
            "user": user,
            "payment_id": 1007,
            "amount": "0.00",
        },
    )

    assert CustomerLoyaltyAccount.objects.count() == 0
    assert LoyaltyTransaction.objects.count() == 0


def test_existing_account_reuses_its_program_and_updates_tier(user):
    custom_program = LoyaltyProgram.objects.create(name="Custom Program", is_active=True)
    LoyaltyTier.objects.create(program=custom_program, name="Bronze", min_points=0, discount_percent="0.00")
    LoyaltyTier.objects.create(program=custom_program, name="Silver", min_points=100, discount_percent="5.00")
    LoyaltyTier.objects.create(program=custom_program, name="Gold", min_points=500, discount_percent="10.00")
    account = CustomerLoyaltyAccount.objects.create(customer=user, program=custom_program, points=90)

    emit_event(
        "payment_completed",
        {
            "user": user,
            "payment_id": 1008,
            "amount": "20.00",
        },
    )

    account.refresh_from_db()
    assert account.points == 110
    assert account.tier.name == "Silver"
