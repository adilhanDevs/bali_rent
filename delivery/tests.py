from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import DeliveryZone
from decimal import Decimal

class DeliveryTests(APITestCase):
    def setUp(self):
        # Create a free zone
        self.free_zone = DeliveryZone.objects.create(
            name='Free Zone',
            center_lat=-8.65,
            center_lng=115.13,
            radius_km=2.0,
            free_delivery=True,
            base_price_usd=0.00,
            price_per_km_usd=0.00,
            is_active=True
        )
        # Create a paid zone
        self.paid_zone = DeliveryZone.objects.create(
            name='Paid Zone',
            center_lat=-8.70,
            center_lng=115.15,
            radius_km=5.0,
            free_delivery=False,
            base_price_usd=5.00,
            price_per_km_usd=1.00,
            is_active=True
        )

    def test_calculate_free_delivery(self):
        url = reverse('delivery_calculate')
        data = {
            "latitude": -8.651,
            "longitude": 115.131
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_free'])
        self.assertEqual(Decimal(response.data['price']), Decimal("0.00"))
        self.assertEqual(response.data['zone']['name'], 'Free Zone')

    def test_calculate_paid_delivery(self):
        url = reverse('delivery_calculate')
        data = {
            "latitude": -8.701,
            "longitude": 115.151
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_free'])
        self.assertGreater(Decimal(response.data['price']), Decimal("5.00"))
        self.assertEqual(response.data['zone']['name'], 'Paid Zone')

    def test_calculate_outside_delivery(self):
        url = reverse('delivery_calculate')
        data = {
            "latitude": -9.000,
            "longitude": 116.000
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_free'])
        self.assertEqual(Decimal(response.data['price']), Decimal("25.00"))
        self.assertIsNone(response.data['zone'])
