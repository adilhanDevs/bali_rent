from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.models import Booking
from catalog.models import Vehicle, VehicleModel, VehicleType
from payments.models import Payment
from users.models import User


class AdminDeleteScooterTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin-delete',
            email='admin-delete@example.com',
            password='adminpass123',
            role='admin',
        )
        self.customer = User.objects.create_user(
            username='customer-delete',
            email='customer-delete@example.com',
            password='customerpass123',
            role='client',
        )

        vehicle_type = VehicleType.objects.create(code='force-delete-scooter', name='Force Delete Scooter')
        vehicle_model = VehicleModel.objects.create(
            name='Force Delete Model',
            brand='Yamaha',
            type=vehicle_type,
            engine_cc=155,
            transmission='automatic',
            fuel_consumption=2.1,
            year=2024,
            trunk='medium',
            helmets_count=2,
            description='QA model',
            rental_terms='QA terms',
        )
        self.vehicle = Vehicle.objects.create(
            model=vehicle_model,
            title='Delete Me',
            slug='delete-me-force',
            sku='DELETE-ME-FORCE-001',
            color='black',
            base_price_usd='30.00',
            status='available',
        )

        now = timezone.now()
        self.booking = Booking.objects.create(
            public_number='BK-FORCE-DELETE-001',
            user=self.customer,
            vehicle=self.vehicle,
            start_at=now + timedelta(days=1),
            end_at=now + timedelta(days=3),
            payment_method='online_card',
            subtotal_usd='60.00',
            addons_total_usd='0.00',
            discount_usd='0.00',
            markup_usd='0.00',
            total_usd='60.00',
            total_display='$60.00',
            status='created',
        )
        self.payment = Payment.objects.create(
            booking=self.booking,
            provider='stripe',
            method='card',
            amount_usd='60.00',
            amount_display='$60.00',
            currency='USD',
            status='pending',
        )
        self.client.force_authenticate(user=self.admin_user)

    def test_admin_can_force_delete_scooter_with_bookings_and_payments(self):
        response = self.client.delete(f'/api/v1/admin/scooters/{self.vehicle.pk}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Payment.objects.filter(pk=self.payment.pk).exists())
        self.assertFalse(Booking.objects.filter(pk=self.booking.pk).exists())
        self.assertFalse(Vehicle.objects.filter(pk=self.vehicle.pk).exists())
