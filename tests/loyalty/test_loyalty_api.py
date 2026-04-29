import pytest

from loyalty.models import (
    CustomerLoyaltyAccount,
    LoyaltyProgram,
    LoyaltyTier,
    LoyaltyTransaction,
    ReferralCode,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def program():
    return LoyaltyProgram.objects.create(name="Main Program", is_active=True)


@pytest.fixture
def second_program():
    return LoyaltyProgram.objects.create(name="Second Program", is_active=True)


@pytest.fixture
def silver_tier(program):
    return LoyaltyTier.objects.create(program=program, name="Silver", min_points=0, discount_percent="5.00")


@pytest.fixture
def gold_tier(program):
    return LoyaltyTier.objects.create(program=program, name="Gold", min_points=100, discount_percent="10.00")


def test_admin_loyalty_program_and_tier_crud_and_validation(admin_client, program):
    program_list = admin_client.get("/api/v1/admin/loyalty/programs/")
    assert program_list.status_code == 200

    create_program = admin_client.post(
        "/api/v1/admin/loyalty/programs/",
        {"name": "VIP Program", "is_active": True},
        format="json",
    )
    assert create_program.status_code == 201
    program_id = create_program.data["id"]

    patch_program = admin_client.patch(
        f"/api/v1/admin/loyalty/programs/{program_id}/",
        {"is_active": False},
        format="json",
    )
    assert patch_program.status_code == 200

    create_tier = admin_client.post(
        "/api/v1/admin/loyalty/tiers/",
        {
            "program_id": program_id,
            "name": "VIP",
            "min_points": 250,
            "discount_percent": "15.00",
        },
        format="json",
    )
    assert create_tier.status_code == 201
    tier_id = create_tier.data["id"]

    invalid_tier = admin_client.post(
        "/api/v1/admin/loyalty/tiers/",
        {
            "program_id": program.id,
            "name": "Broken",
            "min_points": -1,
            "discount_percent": "-2.00",
        },
        format="json",
    )
    assert invalid_tier.status_code == 400
    assert "min_points" in invalid_tier.data or "discount_percent" in invalid_tier.data

    delete_tier = admin_client.delete(f"/api/v1/admin/loyalty/tiers/{tier_id}/")
    assert delete_tier.status_code == 204

    missing_program = admin_client.get("/api/v1/admin/loyalty/programs/999999/")
    assert missing_program.status_code == 404


def test_manager_public_loyalty_crud_business_logic_and_pagination(
    manager_client,
    user,
    program,
    second_program,
    silver_tier,
    gold_tier,
):
    create_account = manager_client.post(
        "/api/v1/loyalty/accounts/",
        {"customer_id": user.id, "program_id": program.id, "points": 10},
        format="json",
    )
    assert create_account.status_code == 201
    account_id = create_account.data["id"]

    second_user_id = user.id
    list_response = manager_client.get("/api/v1/loyalty/accounts/?page_size=1")
    assert list_response.status_code == 200
    assert list_response.data["count"] == 1
    assert len(list_response.data["results"]) == 1

    patch_account = manager_client.patch(
        f"/api/v1/loyalty/accounts/{account_id}/",
        {"points": 20},
        format="json",
    )
    assert patch_account.status_code == 200

    earn_tx = manager_client.post(
        "/api/v1/loyalty/transactions/",
        {"account_id": account_id, "points": 100, "type": "earn"},
        format="json",
    )
    assert earn_tx.status_code == 201
    tx_id = earn_tx.data["id"]

    account = CustomerLoyaltyAccount.objects.get(pk=account_id)
    assert account.points == 120
    assert account.tier_id == gold_tier.id

    patch_tx = manager_client.patch(
        f"/api/v1/loyalty/transactions/{tx_id}/",
        {"points": 80},
        format="json",
    )
    assert patch_tx.status_code == 200
    account.refresh_from_db()
    assert account.points == 100

    invalid_spend = manager_client.post(
        "/api/v1/loyalty/transactions/",
        {"account_id": account_id, "points": 1000, "type": "spend"},
        format="json",
    )
    assert invalid_spend.status_code == 400
    assert "points" in invalid_spend.data

    referral_create = manager_client.post(
        "/api/v1/loyalty/referral-codes/",
        {"user_id": second_user_id, "code": "REF-MAIN-001"},
        format="json",
    )
    assert referral_create.status_code == 201
    referral_id = referral_create.data["id"]

    referral_patch = manager_client.patch(
        f"/api/v1/loyalty/referral-codes/{referral_id}/",
        {"code": "REF-MAIN-002"},
        format="json",
    )
    assert referral_patch.status_code == 200

    delete_tx = manager_client.delete(f"/api/v1/loyalty/transactions/{tx_id}/")
    assert delete_tx.status_code == 204

    delete_referral = manager_client.delete(f"/api/v1/loyalty/referral-codes/{referral_id}/")
    assert delete_referral.status_code == 204

    delete_account = manager_client.delete(f"/api/v1/loyalty/accounts/{account_id}/")
    assert delete_account.status_code == 204

    mismatched_tier = manager_client.post(
        "/api/v1/loyalty/accounts/",
        {
            "customer_id": user.id,
            "program_id": second_program.id,
            "points": 0,
            "tier_id": silver_tier.id,
        },
        format="json",
    )
    assert mismatched_tier.status_code == 400
    assert "tier_id" in mismatched_tier.data


def test_loyalty_permissions_for_staff_client_and_anonymous(
    api_client,
    auth_client,
    staff_client,
    program,
):
    anonymous = api_client.get("/api/v1/loyalty/accounts/")
    assert anonymous.status_code in {401, 403}

    client_forbidden = auth_client.get("/api/v1/loyalty/accounts/")
    assert client_forbidden.status_code == 403

    staff_read = staff_client.get("/api/v1/loyalty/accounts/")
    assert staff_read.status_code == 200

    staff_write = staff_client.post(
        "/api/v1/loyalty/accounts/",
        {"customer_id": 1, "program_id": program.id, "points": 0},
        format="json",
    )
    assert staff_write.status_code == 403


def test_loyalty_404_duplicates_invalid_payloads_and_long_values(
    manager_client,
    user,
    program,
    silver_tier,
):
    missing_program = manager_client.get("/api/v1/admin/loyalty/programs/999999/")
    assert missing_program.status_code == 404

    create_account = manager_client.post(
        "/api/v1/loyalty/accounts/",
        {"customer_id": user.id, "program_id": program.id, "points": 0},
        format="json",
    )
    assert create_account.status_code == 201

    duplicate_account = manager_client.post(
        "/api/v1/loyalty/accounts/",
        {"customer_id": user.id, "program_id": program.id, "points": 1},
        format="json",
    )
    assert duplicate_account.status_code == 400

    invalid_tx_type = manager_client.post(
        "/api/v1/loyalty/transactions/",
        {"account_id": create_account.data["id"], "points": 10, "type": "broken"},
        format="json",
    )
    assert invalid_tx_type.status_code == 400
    assert "type" in invalid_tx_type.data

    empty_referral = manager_client.post("/api/v1/loyalty/referral-codes/", {}, format="json")
    assert empty_referral.status_code == 400

    long_referral = manager_client.post(
        "/api/v1/loyalty/referral-codes/",
        {"user_id": user.id, "code": "x" * 101},
        format="json",
    )
    assert long_referral.status_code == 400
    assert "code" in long_referral.data

    bad_fk = manager_client.post(
        "/api/v1/loyalty/accounts/",
        {"customer_id": 999999, "program_id": program.id, "points": 0, "tier_id": silver_tier.id},
        format="json",
    )
    assert bad_fk.status_code == 400
    assert "customer_id" in bad_fk.data


@pytest.mark.django_db(transaction=True)
def test_loyalty_spend_failure_rolls_back_balance(manager_client, user, program):
    account = CustomerLoyaltyAccount.objects.create(customer=user, program=program, points=20)

    response = manager_client.post(
        "/api/v1/loyalty/transactions/",
        {"account_id": account.id, "points": 50, "type": "spend"},
        format="json",
    )
    assert response.status_code == 400

    account.refresh_from_db()
    assert account.points == 20
    assert account.transactions.count() == 0


def test_loyalty_queries_and_deleted_resources(manager_client, user, program):
    account = CustomerLoyaltyAccount.objects.create(customer=user, program=program, points=5)
    referral = ReferralCode.objects.create(user=user, code="REF-DELETE-ME")

    delete_response = manager_client.delete(f"/api/v1/loyalty/referral-codes/{referral.id}/")
    assert delete_response.status_code == 204

    deleted_referral = manager_client.get(f"/api/v1/loyalty/referral-codes/{referral.id}/")
    assert deleted_referral.status_code == 404

    tx = LoyaltyTransaction.objects.create(account=account, points=5, type="earn")
    with pytest.raises(LoyaltyTransaction.DoesNotExist):
        LoyaltyTransaction.objects.get(pk=999999)


def test_loyalty_account_list_query_count(manager_client, user, program, django_assert_num_queries):
    CustomerLoyaltyAccount.objects.create(customer=user, program=program, points=15)

    with django_assert_num_queries(3, exact=False):
        response = manager_client.get("/api/v1/loyalty/accounts/")

    assert response.status_code == 200


def test_loyalty_model_validation_and_delete_guard(user, program, second_program, silver_tier):
    with pytest.raises(Exception):
        LoyaltyTier.objects.create(program=program, name="Broken", min_points=-1, discount_percent="1.00")

    with pytest.raises(Exception):
        CustomerLoyaltyAccount.objects.create(customer=user, program=second_program, points=0, tier=silver_tier)

    account = CustomerLoyaltyAccount.objects.create(customer=user, program=program, points=10)
    earn = LoyaltyTransaction.objects.create(account=account, points=10, type="earn")
    LoyaltyTransaction.objects.create(account=account, points=20, type="spend")

    with pytest.raises(Exception):
        earn.delete()

    account.refresh_from_db()
    assert str(account).endswith(program.name)
    assert "Silver" in str(silver_tier)


def test_loyalty_update_tier_commit_and_serializer_paths(manager_client, user, program, gold_tier):
    account = CustomerLoyaltyAccount.objects.create(customer=user, program=program, points=10)
    account.points = 150
    account.update_tier(commit=False)
    assert account.tier_id == gold_tier.id
    account.save()

    invalid_patch = manager_client.patch(
        f"/api/v1/loyalty/accounts/{account.id}/",
        {"tier_id": 999999},
        format="json",
    )
    assert invalid_patch.status_code == 400
