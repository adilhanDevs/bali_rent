import pytest
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from notifications.models import Notification
from notifications.models import NotificationLog
from notifications.services import NotificationService
from payments.models import Payment
from users.models import UserDevice


pytestmark = pytest.mark.django_db


def test_notifications_list_read_mark_all_and_owner_access(api_client, auth_client, user):
    own_one = Notification.objects.create(user=user, title="Mine 1", body="Body 1", type="manual")
    own_two = Notification.objects.create(user=user, title="Mine 2", body="Body 2", type="manual")

    from django.contrib.auth import get_user_model

    other_user = get_user_model().objects.create_user(
        username="notify-other",
        email="notify-other@example.com",
        password="testpass123",
        full_name="Notify Other",
        phone="+996555000444",
        role="client",
    )
    other_notification = Notification.objects.create(
        user=other_user,
        title="Other",
        body="Body",
        type="manual",
    )

    unauthorized = api_client.get("/api/v1/notifications/")
    assert unauthorized.status_code == 401

    list_response = auth_client.get("/api/v1/notifications/")
    assert list_response.status_code == 200
    assert list_response.data["count"] == 2

    read_response = auth_client.post(f"/api/v1/notifications/{own_one.id}/read/")
    assert read_response.status_code == 200
    own_one.refresh_from_db()
    assert own_one.is_read is True

    other_read = auth_client.post(f"/api/v1/notifications/{other_notification.id}/read/")
    assert other_read.status_code == 404

    mark_all = auth_client.post("/api/v1/notifications/mark-all-read/")
    assert mark_all.status_code == 200
    own_two.refresh_from_db()
    assert own_two.is_read is True


def test_register_device_success_validation_and_unauthorized(api_client, auth_client):
    unauthorized = api_client.post(
        "/api/v1/notifications/register-device/",
        {"fcm_token": "no-auth", "platform": "ios", "device_id": "dev-1", "app_version": "1.0.0"},
        format="json",
    )
    assert unauthorized.status_code == 401

    success = auth_client.post(
        "/api/v1/notifications/register-device/",
        {
            "fcm_token": "token-1",
            "platform": "android",
            "device_id": "device-1",
            "app_version": "1.0.0",
        },
        format="json",
    )
    assert success.status_code == 200
    assert UserDevice.objects.filter(fcm_token="token-1").exists()

    invalid = auth_client.post(
        "/api/v1/notifications/register-device/",
        {"fcm_token": "token-2", "platform": "android"},
        format="json",
    )
    assert invalid.status_code == 400
    assert "device_id" in invalid.data


def test_admin_notification_send_permissions_validation_and_not_found(
    admin_client,
    staff_client,
    auth_client,
    user,
    mock_notification_side_effects,
):
    success = admin_client.post(
        "/api/v1/admin/notifications/send/",
        {
            "target": "user",
            "user_id": user.id,
            "title": "Broadcast",
            "message": "Hello from admin",
            "data": {"source": "admin"},
        },
        format="json",
    )
    assert success.status_code == 200
    created = Notification.objects.get(type="admin_broadcast")
    assert created.user_id == user.id
    assert created.body == "Hello from admin"
    assert mock_notification_side_effects

    staff_allowed = staff_client.post(
        "/api/v1/admin/notifications/send/",
        {
            "target": "user",
            "user_id": user.id,
            "title": "Staff send",
            "body": "Allowed by IsAdminUser",
        },
        format="json",
    )
    assert staff_allowed.status_code == 200

    forbidden = auth_client.post(
        "/api/v1/admin/notifications/send/",
        {
            "target": "user",
            "user_id": user.id,
            "title": "Forbidden",
            "body": "No access",
        },
        format="json",
    )
    assert forbidden.status_code == 403

    invalid = admin_client.post(
        "/api/v1/admin/notifications/send/",
        {"target": "user", "user_id": user.id, "title": "Broken"},
        format="json",
    )
    assert invalid.status_code == 400
    assert "body" in invalid.data

    missing_user = admin_client.post(
        "/api/v1/admin/notifications/send/",
        {"target": "user", "user_id": 999999, "title": "Broken", "body": "No user"},
        format="json",
    )
    assert missing_user.status_code == 404


def test_notifications_404_invalid_json_and_idempotent_read(auth_client, user):
    notification = Notification.objects.create(user=user, title="Read twice", body="Body", type="manual")

    first = auth_client.post(f"/api/v1/notifications/{notification.id}/read/")
    second = auth_client.post(f"/api/v1/notifications/{notification.id}/read/")
    assert first.status_code == 200
    assert second.status_code == 200

    missing = auth_client.post("/api/v1/notifications/999999/read/")
    assert missing.status_code == 404

    notification.delete()
    deleted = auth_client.post(f"/api/v1/notifications/{notification.id}/read/")
    assert deleted.status_code == 404

    invalid_json = auth_client.generic(
        "POST",
        "/api/v1/notifications/register-device/",
        b'{"fcm_token": "bad"',
        content_type="application/json",
    )
    assert invalid_json.status_code == 400


def test_admin_notification_send_all_and_segment_are_mocked(
    admin_client,
    admin_user,
    manager_user,
    staff_user,
    mock_notification_side_effects,
):
    send_all = admin_client.post(
        "/api/v1/admin/notifications/send/",
        {"target": "all", "title": "Global", "body": "Everyone"},
        format="json",
    )
    assert send_all.status_code == 200
    assert Notification.objects.filter(title="Global").count() >= 3

    send_segment = admin_client.post(
        "/api/v1/admin/notifications/send/",
        {"target": "segment", "segment": "staff", "title": "Staff only", "body": "Segment"},
        format="json",
    )
    assert send_segment.status_code == 200
    assert Notification.objects.filter(title="Staff only", user=staff_user).exists()
    assert Notification.objects.filter(title="Staff only", user=manager_user).exists() is False
    assert mock_notification_side_effects


def test_notifications_list_query_count(auth_client, user, django_assert_num_queries):
    Notification.objects.create(user=user, title="One", body="One", type="manual")
    Notification.objects.create(user=user, title="Two", body="Two", type="manual")

    with django_assert_num_queries(2):
        response = auth_client.get("/api/v1/notifications/")

    assert response.status_code == 200


def test_notification_service_idempotency_and_helpers(user, mock_notification_side_effects):
    first = NotificationService.create_notification(
        user=user,
        title="Once",
        body="Only once",
        notification_type="manual",
        data_json={"a": 1},
        event_key="evt-1",
    )
    second = NotificationService.create_notification(
        user=user,
        title="Once",
        body="Only once",
        notification_type="manual",
        data_json={"a": 1},
        event_key="evt-1",
    )
    by_user_id = NotificationService.create_notification_by_user_id(
        user_id=user.id,
        title="By id",
        body="Created by helper",
        notification_type="manual",
    )

    assert first.id == second.id
    assert by_user_id.user_id == user.id
    assert NotificationLog.objects.filter(event_key="evt-1").count() == 1
    assert mock_notification_side_effects


def test_notification_dispatch_send_push_and_signal_paths(settings, user, vehicle, mock_notification_side_effects):
    from bookings.models import Booking

    now = timezone.now()
    booking = Booking.objects.create(
        public_number="BK-NOTIFY-001",
        user=user,
        vehicle=vehicle,
        start_at=now + timedelta(days=1),
        end_at=now + timedelta(days=2),
        payment_method="online_card",
        currency="USD",
        subtotal_usd=Decimal("100.00"),
        addons_total_usd=Decimal("0.00"),
        delivery_price_usd=Decimal("0.00"),
        discount_usd=Decimal("0.00"),
        markup_usd=Decimal("0.00"),
        total_usd=Decimal("100.00"),
        total_display="USD 100.00",
        status="created",
    )

    assert Notification.objects.filter(type="booking_created", user=user).count() == 1

    booking.status = "confirmed"
    booking.save()
    booking.save()
    assert Notification.objects.filter(type="booking_confirmed", user=user).count() == 1

    payment = Payment.objects.create(
        booking=booking,
        provider="stripe",
        method="card",
        amount_usd=Decimal("100.00"),
        amount_display="USD 100.00",
        currency="USD",
        status="pending",
        provider_payment_id="pay-1",
    )
    payment.status = "succeeded"
    payment.save()
    payment.save()
    assert Notification.objects.filter(type="payment_success", user=user).count() == 1

    settings.NOTIFICATIONS_USE_CELERY = True

    class DummyTask:
        called = False

        @classmethod
        def delay(cls, *args, **kwargs):
            cls.called = True

    import notifications.tasks

    original_task = notifications.tasks.create_notification_task
    notifications.tasks.create_notification_task = DummyTask
    try:
        result = NotificationService.dispatch_notification(
            user=user,
            title="Async",
            body="Async body",
            notification_type="manual",
            data_json={"mode": "celery"},
        )
        assert result is None
        assert DummyTask.called is True
    finally:
        notifications.tasks.create_notification_task = original_task

    class FailingTask:
        @classmethod
        def delay(cls, *args, **kwargs):
            raise RuntimeError("boom")

    notifications.tasks.create_notification_task = FailingTask
    try:
        fallback = NotificationService.dispatch_notification(
            user=user,
            title="Fallback",
            body="Fallback body",
            notification_type="manual",
            data_json={"mode": "fallback"},
        )
        assert fallback is not None
    finally:
        notifications.tasks.create_notification_task = original_task

    UserDevice.objects.create(
        user=user,
        fcm_token="push-1",
        platform="ios",
        device_id="dev-1",
        app_version="1.0.0",
        is_active=True,
    )
    NotificationService.send_push = staticmethod(mock_notification_side_effects.original_send_push)
    NotificationService.send_push(user, "Push", "Body", {"x": 1})
    settings.FCM_SERVER_KEY = "configured"
    NotificationService.send_push(user, "Push", "Body", {"x": 1})
    assert mock_notification_side_effects


def test_notification_service_integrity_error_fallback(user, monkeypatch):
    notification = Notification.objects.create(user=user, title="Existing", body="Body", type="manual")
    log = NotificationLog.objects.create(
        notification=notification,
        user=user,
        event_type="manual",
        event_key="dup-event",
        channel="in_app",
        status="sent",
    )

    class FakeSelectRelated:
        def filter(self, **kwargs):
            class FakeFilter:
                def first(self_inner):
                    return None

            return FakeFilter()

        def get(self, **kwargs):
            return log

    def raise_integrity(*args, **kwargs):
        from django.db import IntegrityError

        raise IntegrityError("duplicate")

    monkeypatch.setattr("notifications.services.NotificationLog.objects.select_related", lambda *args, **kwargs: FakeSelectRelated())
    monkeypatch.setattr("notifications.services.NotificationLog.objects.create", raise_integrity)

    resolved = NotificationService.create_notification(
        user=user,
        title="Race",
        body="Race body",
        notification_type="manual",
        event_key="dup-event",
    )
    assert resolved.id == notification.id
