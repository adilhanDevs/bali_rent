from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from bookings.models import Booking
from catalog.models import Vehicle, VehicleModel, VehicleType


User = get_user_model()


@pytest.fixture(autouse=True)
def isolated_media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.NOTIFICATIONS_USE_CELERY = False
    return settings.MEDIA_ROOT


@pytest.fixture(autouse=True)
def mock_notification_side_effects(monkeypatch):
    class PushCalls(list):
        pass

    push_calls = PushCalls()
    from notifications.services import NotificationService

    original_send_push = NotificationService.send_push

    def fake_send_push(user, title, body, data=None):
        push_calls.append(
            {
                "user_id": user.id,
                "title": title,
                "body": body,
                "data": data,
            }
        )

    monkeypatch.setattr(
        "notifications.services.NotificationService.send_push",
        staticmethod(fake_send_push),
    )
    push_calls.original_send_push = original_send_push
    return push_calls


@pytest.fixture
def api_client():
    return APIClient()


def _create_user(*, email, username, role="client", is_staff=False, is_superuser=False):
    return User.objects.create_user(
        username=username,
        email=email,
        password="testpass123",
        full_name=f"{role.title()} {username}",
        phone=f"+996{uuid4().int % 10**9:09d}",
        role=role,
        is_staff=is_staff,
        is_superuser=is_superuser,
    )


@pytest.fixture
def user(db):
    return _create_user(email="client@example.com", username="client", role="client")


@pytest.fixture
def admin_user(db):
    return _create_user(
        email="admin@example.com",
        username="admin",
        role="admin",
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def second_user(db):
    return _create_user(email="second@example.com", username="second", role="client")


@pytest.fixture
def manager_user(db):
    return _create_user(
        email="manager@example.com",
        username="manager",
        role="manager",
        is_staff=True,
    )


@pytest.fixture
def staff_user(db):
    return _create_user(
        email="staff@example.com",
        username="staff",
        role="staff",
        is_staff=True,
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def manager_client(manager_user):
    client = APIClient()
    client.force_authenticate(user=manager_user)
    return client


@pytest.fixture
def staff_client(staff_user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client


@pytest.fixture
def vehicle_type(db):
    return VehicleType.objects.create(code=f"scooter-{uuid4().hex[:6]}", name="Scooter")


@pytest.fixture
def vehicle_model(vehicle_type):
    return VehicleModel.objects.create(
        name="NMAX",
        brand="Yamaha",
        type=vehicle_type,
        engine_cc=155,
        transmission="automatic",
        fuel_consumption=2.5,
        year=2024,
        trunk="medium",
        helmets_count=2,
        description="Comfortable scooter",
        rental_terms="Standard rental terms",
    )


@pytest.fixture
def vehicle(vehicle_model):
    suffix = uuid4().hex[:8]
    return Vehicle.objects.create(
        model=vehicle_model,
        title=f"Yamaha NMAX {suffix}",
        slug=f"yamaha-nmax-{suffix}",
        sku=f"NMAX-{suffix}",
        color="black",
        base_price_usd=Decimal("25.00"),
        status="available",
    )


@pytest.fixture
def booking(user, vehicle):
    now = timezone.now()
    return Booking.objects.create(
        public_number=f"BK-{uuid4().hex[:8].upper()}",
        user=user,
        vehicle=vehicle,
        start_at=now + timedelta(days=2),
        end_at=now + timedelta(days=5),
        payment_method="online_card",
        currency="USD",
        subtotal_usd=Decimal("100.00"),
        addons_total_usd=Decimal("0.00"),
        delivery_price_usd=Decimal("0.00"),
        discount_usd=Decimal("0.00"),
        markup_usd=Decimal("0.00"),
        total_usd=Decimal("100.00"),
        total_display="USD 100.00",
        status="completed",
    )
