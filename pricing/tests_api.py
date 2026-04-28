from django.test import TestCase
from decimal import Decimal
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from catalog.models import Vehicle, VehicleModel, VehicleType
from pricing.models import (
    Season, ScooterSeasonPrice, OccupancyPricingRule, 
    DevicePricingRule, GeoPricingRule, PriceCalculationLog
)
from datetime import timedelta
from django.contrib.auth import get_user_model

User = get_user_model()

class PricingAPITest(APITestCase):
    def setUp(self):
        self.vt = VehicleType.objects.create(code='scooter', name='Scooter')
        self.vm = VehicleModel.objects.create(
            name='NMAX', brand='Yamaha', type=self.vt, engine_cc=155,
            transmission='auto', fuel_consumption=2.5, year=2023,
            trunk='large', helmets_count=2, description='test', rental_terms='test'
        )
        self.vehicle = Vehicle.objects.create(
            model=self.vm, title='Yamaha NMAX', slug='nmax-1', sku='NMAX001',
            color='Black', base_price_usd=Decimal('20.00'), status='available'
        )
        self.user = User.objects.create_user(email='test@example.com', username='test', password='password', role='client')
        self.admin = User.objects.create_superuser(email='admin@example.com', username='admin', password='password', role='admin')
        
        self.calculate_url = reverse('pricing-calculate')

    def test_public_price_calculation_success(self):
        data = {
            "vehicle_id": self.vehicle.id,
            "start_at": (timezone.now() + timedelta(days=1)).isoformat(),
            "end_at": (timezone.now() + timedelta(days=2)).isoformat()
        }
        response = self.client.post(self.calculate_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('final_price', response.data)
        self.assertIn('price_calculation_id', response.data)
        # Check internal logic not exposed
        self.assertNotIn('steps', response.data)
        self.assertNotIn('calculation_snapshot', response.data)

    def test_invalid_payload(self):
        data = {
            "vehicle_id": 9999, # non-existent
            "start_at": "not-a-date"
        }
        response = self.client.post(self.calculate_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_crud_protected(self):
        url = reverse('admin-season-list')
        
        # Unauthorized
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Client (non-admin)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Admin
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_create_rule(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('admin-season-list')
        data = {
            "name": "Summer 2026",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
            "is_active": True
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Season.objects.count(), 1)
