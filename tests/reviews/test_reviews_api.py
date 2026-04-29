import pytest

from reviews.models import Review
from reviews.views import AdminReviewViewSet, ReviewViewSet


pytestmark = pytest.mark.django_db


@pytest.fixture
def second_user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        username="review-second",
        email="review-second@example.com",
        password="testpass123",
        full_name="Review Second",
        phone="+996555000555",
        role="client",
    )


@pytest.fixture
def second_booking(second_user, vehicle):
    from bookings.models import Booking
    from datetime import timedelta
    from decimal import Decimal
    from django.utils import timezone
    from uuid import uuid4

    now = timezone.now()
    return Booking.objects.create(
        public_number=f"BK-{uuid4().hex[:8].upper()}",
        user=second_user,
        vehicle=vehicle,
        start_at=now + timedelta(days=1),
        end_at=now + timedelta(days=2),
        payment_method="online_card",
        currency="USD",
        subtotal_usd=Decimal("50.00"),
        addons_total_usd=Decimal("0.00"),
        delivery_price_usd=Decimal("0.00"),
        discount_usd=Decimal("0.00"),
        markup_usd=Decimal("0.00"),
        total_usd=Decimal("50.00"),
        total_display="USD 50.00",
        status="completed",
    )


def test_reviews_list_create_visibility_and_unauthorized(api_client, auth_client, booking, vehicle):
    list_response = api_client.get("/api/v1/reviews/")
    assert list_response.status_code == 200
    assert list_response.data["count"] == 0

    unauthorized = api_client.post(
        "/api/v1/reviews/",
        {"booking": booking.id, "scooter": vehicle.id, "rating": 5, "comment": "Great"},
        format="json",
    )
    assert unauthorized.status_code == 401

    create_response = auth_client.post(
        "/api/v1/reviews/",
        {"booking": booking.id, "scooter": vehicle.id, "rating": 5, "comment": "Great"},
        format="json",
    )
    assert create_response.status_code == 201
    review_id = create_response.data["id"]

    own_detail = auth_client.get(f"/api/v1/reviews/{review_id}/")
    assert own_detail.status_code == 200

    public_list = api_client.get("/api/v1/reviews/")
    assert public_list.status_code == 200
    assert public_list.data["count"] == 0

    owner_patch = auth_client.patch(
        f"/api/v1/reviews/{review_id}/",
        {"comment": "Updated comment"},
        format="json",
    )
    assert owner_patch.status_code == 200

    owner_delete = auth_client.delete(f"/api/v1/reviews/{review_id}/")
    assert owner_delete.status_code == 204


def test_reviews_validation_errors(auth_client, booking, second_booking, vehicle):
    invalid_rating = auth_client.post(
        "/api/v1/reviews/",
        {"booking": booking.id, "scooter": vehicle.id, "rating": 6, "comment": "Too high"},
        format="json",
    )
    assert invalid_rating.status_code == 400
    assert "rating" in invalid_rating.data

    other_booking = auth_client.post(
        "/api/v1/reviews/",
        {"booking": second_booking.id, "scooter": vehicle.id, "rating": 5, "comment": "Not mine"},
        format="json",
    )
    assert other_booking.status_code == 400

    booking.status = "active"
    booking.save(update_fields=["status"])
    incomplete_booking = auth_client.post(
        "/api/v1/reviews/",
        {"booking": booking.id, "scooter": vehicle.id, "rating": 5, "comment": "Too early"},
        format="json",
    )
    assert incomplete_booking.status_code == 400


def test_reviews_permissions_admin_actions_and_forbidden_updates(
    api_client,
    auth_client,
    admin_client,
    second_user,
    booking,
    vehicle,
):
    review = Review.objects.create(
        booking=booking,
        scooter=vehicle,
        user=booking.user,
        rating=4,
        comment="Pending review",
        status="pending",
    )

    other_client = api_client
    other_client.force_authenticate(user=second_user)

    hidden_pending = other_client.get(f"/api/v1/reviews/{review.id}/")
    assert hidden_pending.status_code == 404

    approve = admin_client.post(f"/api/v1/admin/reviews/{review.id}/approve/")
    assert approve.status_code == 200
    review.refresh_from_db()
    assert review.status == "approved"

    admin_list = admin_client.get("/api/v1/admin/reviews/")
    assert admin_list.status_code == 200

    forbidden_patch = other_client.patch(
        f"/api/v1/reviews/{review.id}/",
        {"comment": "Trying to overwrite"},
        format="json",
    )
    assert forbidden_patch.status_code == 403

    client_admin_forbidden = auth_client.get("/api/v1/admin/reviews/")
    assert client_admin_forbidden.status_code == 403

    missing_admin_review = admin_client.get("/api/v1/admin/reviews/999999/")
    assert missing_admin_review.status_code == 404


def test_reviews_duplicate_create_empty_payload_invalid_types_and_deleted_404(
    auth_client,
    booking,
    vehicle,
):
    first_create = auth_client.post(
        "/api/v1/reviews/",
        {"booking": booking.id, "scooter": vehicle.id, "rating": 5, "comment": "First"},
        format="json",
    )
    assert first_create.status_code == 201
    review_id = first_create.data["id"]

    duplicate = auth_client.post(
        "/api/v1/reviews/",
        {"booking": booking.id, "scooter": vehicle.id, "rating": 4, "comment": "Duplicate"},
        format="json",
    )
    assert duplicate.status_code == 400

    empty_payload = auth_client.post("/api/v1/reviews/", {}, format="json")
    assert empty_payload.status_code == 400

    broken_types = auth_client.post(
        "/api/v1/reviews/",
        {"booking": "abc", "scooter": "def", "rating": "wrong", "comment": 123},
        format="json",
    )
    assert broken_types.status_code == 400

    delete_response = auth_client.delete(f"/api/v1/reviews/{review_id}/")
    assert delete_response.status_code == 204

    deleted_detail = auth_client.get(f"/api/v1/reviews/{review_id}/")
    assert deleted_detail.status_code == 404


def test_reviews_invalid_json_and_query_count(api_client, auth_client, booking, vehicle, admin_client, django_assert_num_queries):
    invalid_json = auth_client.generic(
        "POST",
        "/api/v1/reviews/",
        b'{"booking":',
        content_type="application/json",
    )
    assert invalid_json.status_code == 400

    review = Review.objects.create(
        booking=booking,
        scooter=vehicle,
        user=booking.user,
        rating=5,
        comment="Approved review",
        status="approved",
    )
    assert review.id

    with django_assert_num_queries(4):
        response = api_client.get("/api/v1/reviews/")

    assert response.status_code == 200


def test_reviews_reject_action_and_stats_helpers(admin_client, booking, vehicle):
    Review.objects.create(
        booking=booking,
        scooter=vehicle,
        user=booking.user,
        rating=4,
        comment="Approved",
        status="approved",
    )
    pending = Review.objects.create(
        scooter=vehicle,
        user=booking.user,
        rating=2,
        comment="Pending",
        status="pending",
    )

    ReviewViewSet().update_scooter_stats(vehicle)
    vehicle.refresh_from_db()
    assert vehicle.reviews_count == 1

    reject = admin_client.post(f"/api/v1/admin/reviews/{pending.id}/reject/")
    assert reject.status_code == 200
    pending.refresh_from_db()
    assert pending.status == "rejected"

    AdminReviewViewSet().update_scooter_stats(vehicle)
    vehicle.refresh_from_db()
    assert vehicle.reviews_count == 1


def test_reviews_queryset_scooter_filter_branch(booking, vehicle):
    review = Review.objects.create(
        booking=booking,
        scooter=vehicle,
        user=booking.user,
        rating=5,
        comment="Filtered",
        status="approved",
    )

    from rest_framework.test import APIRequestFactory
    from django.contrib.auth.models import AnonymousUser

    factory = APIRequestFactory()
    request = factory.get("/api/v1/reviews/")
    request.user = AnonymousUser()
    view = ReviewViewSet()
    view.request = request
    view.kwargs = {"scooter_id": vehicle.id}
    queryset = view.get_queryset()
    assert list(queryset) == [review]
