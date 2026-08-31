from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from bookings.models import AvailabilityBlock, Booking


pytestmark = pytest.mark.django_db


def test_admin_booking_list_includes_scooter_color(admin_client, booking, vehicle):
    response = admin_client.get("/api/v1/admin/bookings/")

    assert response.status_code == 200
    result = response.data["results"][0]
    assert result["id"] == booking.id
    assert result["scooter"] == {
        "id": vehicle.id,
        "title": vehicle.title,
        "sku": vehicle.sku,
        "color": vehicle.color,
    }


def test_admin_can_cancel_booking_and_release_dates(admin_client, user, vehicle):
    start_at = timezone.now() + timedelta(days=7)
    end_at = start_at + timedelta(days=3)
    booking = Booking.objects.create(
        public_number="BK-ADMIN-CANCEL",
        user=user,
        vehicle=vehicle,
        start_at=start_at,
        end_at=end_at,
        payment_method="online_card",
        currency="USD",
        subtotal_usd=Decimal("75.00"),
        addons_total_usd=Decimal("0.00"),
        delivery_price_usd=Decimal("0.00"),
        discount_usd=Decimal("0.00"),
        markup_usd=Decimal("0.00"),
        total_usd=Decimal("75.00"),
        total_display="USD 75.00",
        status="confirmed",
    )
    AvailabilityBlock.objects.create(
        vehicle=vehicle,
        start_at=start_at,
        end_at=end_at,
        type="booking",
        source_booking=booking,
    )

    response = admin_client.post(f"/api/v1/admin/bookings/{booking.id}/cancel/")

    assert response.status_code == 200
    booking.refresh_from_db()
    assert booking.status == "cancelled"
    assert not AvailabilityBlock.objects.filter(source_booking=booking).exists()


def test_admin_can_delete_booking_and_release_dates(admin_client, user, vehicle):
    start_at = timezone.now() + timedelta(days=12)
    end_at = start_at + timedelta(days=2)
    booking = Booking.objects.create(
        public_number="BK-ADMIN-DELETE",
        user=user,
        vehicle=vehicle,
        start_at=start_at,
        end_at=end_at,
        payment_method="online_card",
        currency="USD",
        subtotal_usd=Decimal("50.00"),
        addons_total_usd=Decimal("0.00"),
        delivery_price_usd=Decimal("0.00"),
        discount_usd=Decimal("0.00"),
        markup_usd=Decimal("0.00"),
        total_usd=Decimal("50.00"),
        total_display="USD 50.00",
        status="created",
    )
    block = AvailabilityBlock.objects.create(
        vehicle=vehicle,
        start_at=start_at,
        end_at=end_at,
        type="booking",
        source_booking=booking,
    )

    response = admin_client.delete(f"/api/v1/admin/bookings/{booking.id}/")

    assert response.status_code == 204
    assert not Booking.objects.filter(id=booking.id).exists()
    assert not AvailabilityBlock.objects.filter(id=block.id).exists()
