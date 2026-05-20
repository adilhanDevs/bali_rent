from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch
from django.contrib.auth import get_user_model
from .models import VehicleType, VehicleModel, Vehicle
from bookings.models import AvailabilityBlock
from django.utils import timezone
from datetime import timedelta, datetime

User = get_user_model()

class CatalogTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='catalog-admin',
            email='catalog-admin@example.com',
            password='catalogpass123',
            full_name='Catalog Admin',
            role='admin',
            is_staff=True,
            is_superuser=True,
        )
        self.type = VehicleType.objects.create(code='scooter', name='Scooter')
        self.model = VehicleModel.objects.create(
            name='Vario', brand='Honda', type=self.type, 
            engine_cc=150, transmission='Auto', fuel_consumption=2.0,
            year=2023, trunk='10L', helmets_count=2, description='Desc'
        )
        self.vehicle = Vehicle.objects.create(
            model=self.model, title='Vario 150', slug='vario-150',
            sku='V150', color='Black', base_price_usd=15.00,
            status='available', is_featured=True
        )

    def test_get_scooter_list(self):
        url = reverse('scooter-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_vehicle_type_detail_works_without_translation_table(self):
        url = reverse('scooter-type-detail', args=[self.type.id])
        with patch('catalog.views.vehicle_type_translation_table_available', return_value=False), patch(
            'catalog.serializers.vehicle_type_translation_table_available', return_value=False
        ):
            response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.type.id)
        self.assertEqual(response.data['translations'], [])

    def test_vehicle_type_delete_works_without_translation_table(self):
        removable_type = VehicleType.objects.create(code='removable', name='Removable')
        url = reverse('scooter-type-detail', args=[removable_type.id])
        self.client.force_authenticate(self.admin_user)
        with patch('catalog.views.vehicle_type_translation_table_available', return_value=False):
            response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(VehicleType.objects.filter(pk=removable_type.pk).exists())

    def test_vehicle_type_delete_returns_conflict_when_models_exist(self):
        url = reverse('scooter-type-detail', args=[self.type.id])
        self.client.force_authenticate(self.admin_user)
        with patch('catalog.views.vehicle_type_translation_table_available', return_value=False):
            response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('Cannot delete this scooter type', response.data['error'])

    def test_vehicle_type_translations_write_returns_service_unavailable_without_translation_table(self):
        url = reverse('scooter-type-translations', args=[self.type.id])
        self.client.force_authenticate(self.admin_user)
        with patch('catalog.views.vehicle_type_translation_table_available', return_value=False):
            response = self.client.post(url, [{'language': 'en', 'name': 'Scooter'}], format='json')
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_availability_calendar_full_month(self):
        url = reverse('scooter-availability', args=[self.vehicle.id])
        response = self.client.get(url, {'year': 2026, 'month': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['days']), 31)
        for day in response.data['days']:
            self.assertEqual(day['status'], 'available')

    def test_availability_calendar_booked(self):
        # Create a full day booking
        start = timezone.make_aware(datetime(2026, 5, 10, 0, 0))
        end = timezone.make_aware(datetime(2026, 5, 11, 0, 0))
        AvailabilityBlock.objects.create(
            vehicle=self.vehicle, start_at=start, end_at=end, type='booking'
        )
        
        url = reverse('scooter-availability', args=[self.vehicle.id])
        response = self.client.get(url, {'year': 2026, 'month': 5})
        
        # Day 10 should be booked
        day_10 = next(d for d in response.data['days'] if d['date'] == '2026-05-10')
        self.assertEqual(day_10['status'], 'booked')

    def test_availability_calendar_partially_booked(self):
        # Create a partial day booking
        start = timezone.make_aware(datetime(2026, 5, 15, 10, 0))
        end = timezone.make_aware(datetime(2026, 5, 15, 18, 0))
        AvailabilityBlock.objects.create(
            vehicle=self.vehicle, start_at=start, end_at=end, type='booking'
        )
        
        url = reverse('scooter-availability', args=[self.vehicle.id])
        response = self.client.get(url, {'year': 2026, 'month': 5})
        
        day_15 = next(d for d in response.data['days'] if d['date'] == '2026-05-15')
        self.assertEqual(day_15['status'], 'partially_booked')

    def test_availability_calendar_maintenance(self):
        # Create maintenance block
        start = timezone.make_aware(datetime(2026, 5, 20, 10, 0))
        end = timezone.make_aware(datetime(2026, 5, 20, 18, 0))
        AvailabilityBlock.objects.create(
            vehicle=self.vehicle, start_at=start, end_at=end, type='maintenance'
        )
        
        url = reverse('scooter-availability', args=[self.vehicle.id])
        response = self.client.get(url, {'year': 2026, 'month': 5})
        
        day_20 = next(d for d in response.data['days'] if d['date'] == '2026-05-20')
        self.assertEqual(day_20['status'], 'maintenance')

    def test_availability_calendar_invalid(self):
        url = reverse('scooter-availability', args=[self.vehicle.id])
        response = self.client.get(url, {'year': 2026, 'month': 13})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
