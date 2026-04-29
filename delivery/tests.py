from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Vehicle, VehicleModel, VehicleType

from .models import DeliveryPricingRule, DeliveryZone

User = get_user_model()


class DeliveryTests(APITestCase):
    def setUp(self):
        self.free_zone = DeliveryZone.objects.create(
            name='Free Zone',
            polygon=[
                {'lat': -8.6600, 'lng': 115.1200},
                {'lat': -8.6600, 'lng': 115.1400},
                {'lat': -8.6400, 'lng': 115.1400},
                {'lat': -8.6400, 'lng': 115.1200},
            ],
            is_free=True,
            is_active=True,
            center_lat=-8.65,
            center_lng=115.13,
            radius_km=2.0,
        )
        self.paid_zone = DeliveryZone.objects.create(
            name='Paid Zone',
            polygon=[
                {'lat': -8.7100, 'lng': 115.1400},
                {'lat': -8.7100, 'lng': 115.1700},
                {'lat': -8.6800, 'lng': 115.1700},
                {'lat': -8.6800, 'lng': 115.1400},
            ],
            is_free=False,
            is_active=True,
            center_lat=-8.695,
            center_lng=115.155,
            radius_km=5.0,
        )
        DeliveryPricingRule.objects.create(zone=self.paid_zone, price=Decimal('7.50'), is_active=True)

        self.user = User.objects.create_user(
            email='customer@example.com',
            username='customer',
            password='password123',
            role='client',
        )
        vehicle_type = VehicleType.objects.create(code='scooter', name='Scooter')
        vehicle_model = VehicleModel.objects.create(
            name='NMAX',
            brand='Yamaha',
            type=vehicle_type,
            engine_cc=155,
            transmission='auto',
            fuel_consumption=Decimal('2.40'),
            year=2024,
            trunk='large',
            helmets_count=2,
            description='Test scooter',
            rental_terms='Test terms',
        )
        self.vehicle = Vehicle.objects.create(
            model=vehicle_model,
            title='Yamaha NMAX',
            slug='yamaha-nmax-delivery',
            sku='DLV001',
            color='Black',
            base_price_usd=Decimal('20.00'),
            status='available',
        )

    def test_calculate_free_delivery(self):
        response = self.client.post(
            reverse('delivery_calculate'),
            {'latitude': -8.6500, 'longitude': 115.1300, 'address': 'Canggu center'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_free'])
        self.assertEqual(Decimal(response.data['price']), Decimal('0.00'))
        self.assertEqual(Decimal(response.data['delivery_price']), Decimal('0.00'))
        self.assertEqual(response.data['zone']['name'], 'Free Zone')
        self.assertEqual(response.data['zone_name'], 'Free Zone')
        self.assertEqual(response.data['delivery_point']['address'], 'Canggu center')

    def test_calculate_paid_delivery(self):
        response = self.client.post(
            reverse('delivery_calculate'),
            {'latitude': -8.6950, 'longitude': 115.1550},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_free'])
        self.assertEqual(Decimal(response.data['price']), Decimal('7.50'))
        self.assertEqual(Decimal(response.data['delivery_price']), Decimal('7.50'))
        self.assertEqual(response.data['zone']['name'], 'Paid Zone')
        self.assertEqual(response.data['zone_name'], 'Paid Zone')

    def test_calculate_outside_delivery(self):
        response = self.client.post(
            reverse('delivery_calculate'),
            {'latitude': -9.0000, 'longitude': 116.0000},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_free'])
        self.assertEqual(Decimal(response.data['price']), Decimal('25.00'))
        self.assertEqual(Decimal(response.data['delivery_price']), Decimal('25.00'))
        self.assertIsNone(response.data['zone'])
        self.assertIsNone(response.data['zone_name'])

    def test_calculate_accepts_lat_lng_aliases(self):
        response = self.client.post(
            reverse('delivery_calculate'),
            {'lat': -8.6950, 'lng': 115.1550},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['zone_name'], 'Paid Zone')
        self.assertEqual(Decimal(response.data['delivery_price']), Decimal('7.50'))

    def test_booking_quote_uses_delivery_module(self):
        response = self.client.post(
            '/api/v1/bookings/calculate/',
            {
                'scooter_id': self.vehicle.id,
                'start_datetime': (timezone.now() + timedelta(days=1)).isoformat(),
                'end_datetime': (timezone.now() + timedelta(days=2)).isoformat(),
                'delivery_address': 'Paid zone address',
                'delivery_latitude': -8.6950,
                'delivery_longitude': 115.1550,
                'payment_method': 'online_card',
                'currency': 'USD',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['delivery_price']), Decimal('7.50'))
