import pytest

from notifications.models import Notification
from reviews.models import Review


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("path", "expected_status"),
    [
        ("/api/v1/admin/crm/customer-segments/", 403),
        ("/api/v1/admin/tasks/staff-tasks/", 403),
        ("/api/v1/admin/chat/threads/", 403),
        ("/api/v1/admin/loyalty/programs/", 403),
        ("/api/v1/admin/notifications/send/", 403),
        ("/api/v1/admin/reviews/", 403),
    ],
)
def test_client_cannot_access_admin_dev2_endpoints(auth_client, path, expected_status):
    response = auth_client.get(path)
    assert response.status_code == expected_status


def test_staff_is_read_only_across_dev2_admin_endpoints(staff_client, admin_client, user, vehicle, booking):
    read_paths = [
        "/api/v1/admin/crm/customer-segments/",
        "/api/v1/admin/tasks/staff-tasks/",
        "/api/v1/admin/chat/threads/",
        "/api/v1/admin/loyalty/programs/",
        "/api/v1/admin/reviews/",
    ]
    for path in read_paths:
        assert staff_client.get(path).status_code == 200

    assert staff_client.post("/api/v1/admin/crm/customer-segments/", {"code": "s", "name": "S"}, format="json").status_code == 403
    assert staff_client.post("/api/v1/admin/tasks/staff-tasks/", {"title": "Denied", "description": "Denied"}, format="json").status_code == 403
    assert staff_client.post("/api/v1/admin/chat/quick-replies/", {"title": "Denied", "text": "Denied", "is_active": True}, format="json").status_code == 403
    assert staff_client.post("/api/v1/admin/loyalty/programs/", {"name": "Denied", "is_active": True}, format="json").status_code == 403


def test_owner_boundaries_for_notifications_and_reviews(api_client, auth_client, user, second_user, booking, vehicle):
    notification = Notification.objects.create(user=user, title="Private", body="Body", type="manual")
    review = Review.objects.create(
        booking=booking,
        scooter=vehicle,
        user=user,
        rating=5,
        comment="Private review",
        status="pending",
    )

    other_client = api_client
    other_client.force_authenticate(user=second_user)

    assert other_client.get(f"/api/v1/notifications/{notification.id}/").status_code == 404
    assert other_client.get(f"/api/v1/reviews/{review.id}/").status_code == 404
    assert other_client.patch(f"/api/v1/reviews/{review.id}/", {"comment": "Hack"}, format="json").status_code == 404
