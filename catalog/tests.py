from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch
from django.contrib.auth import get_user_model
from .models import VehicleType, VehicleTypeTranslation, VehicleModel, Vehicle, VehicleTranslation, VehicleImage
from bookings.models import AvailabilityBlock
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
from pricing.models import ScooterRentalRate
import tempfile

User = get_user_model()


TEST_GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
    b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00"
    b"\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


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
            year=2023, trunk='10L', helmets_count=2, description='Desc', rental_terms='Terms'
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

    def test_scooter_list_uses_requested_language_for_title_and_type(self):
        VehicleTypeTranslation.objects.create(vehicle_type=self.type, language='ru', name='Скутер')
        VehicleTranslation.objects.create(
            vehicle=self.vehicle,
            language='ru',
            title='Варио 150',
            description='Русское описание',
            rental_terms='Русские условия',
            transmission='Автомат',
            trunk='Багажник 10л',
            color='Чёрный',
        )

        url = reverse('scooter-list')
        response = self.client.get(url, HTTP_X_LANGUAGE='ru')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data['results'][0]
        self.assertEqual(item['title'], 'Варио 150')
        self.assertEqual(item['type'], 'Скутер')
        self.assertEqual(item['short_description'], 'Русское описание...')

    def test_scooter_detail_uses_requested_language_everywhere(self):
        VehicleTypeTranslation.objects.create(vehicle_type=self.type, language='ru', name='Скутер')
        VehicleTranslation.objects.create(
            vehicle=self.vehicle,
            language='ru',
            title='Варио 150',
            description='Русское описание',
            rental_terms='Русские условия',
            transmission='Автомат',
            trunk='Багажник 10л',
            color='Чёрный',
        )

        url = reverse('scooter-detail', args=[self.vehicle.id])
        response = self.client.get(url, HTTP_X_LANGUAGE='ru')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Варио 150')
        self.assertEqual(response.data['type'], 'Скутер')
        self.assertEqual(response.data['full_description'], 'Русское описание')
        self.assertEqual(response.data['rental_terms'], 'Русские условия')
        self.assertEqual(response.data['characteristics']['transmission'], 'Автомат')
        self.assertEqual(response.data['characteristics']['trunk'], 'Багажник 10л')
        self.assertEqual(response.data['characteristics']['color'], 'Чёрный')

    def test_scooter_list_uses_lowest_tariff_price(self):
        ScooterRentalRate.objects.bulk_create(
            [
                ScooterRentalRate(scooter=self.vehicle, min_days=1, max_days=1, price_usd=Decimal('15.00'), billing_period_days=1),
                ScooterRentalRate(scooter=self.vehicle, min_days=2, max_days=6, price_usd=Decimal('12.00'), billing_period_days=1),
                ScooterRentalRate(scooter=self.vehicle, min_days=7, max_days=15, price_usd=Decimal('10.00'), billing_period_days=1),
                ScooterRentalRate(scooter=self.vehicle, min_days=30, max_days=None, price_usd=Decimal('250.00'), billing_period_days=30),
            ]
        )

        response = self.client.get(reverse('scooter-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['results'][0]['price_per_day']), Decimal('10.00'))

    def test_scooter_detail_returns_pricing_tiers(self):
        ScooterRentalRate.objects.bulk_create(
            [
                ScooterRentalRate(scooter=self.vehicle, min_days=1, max_days=1, price_usd=Decimal('15.00'), billing_period_days=1),
                ScooterRentalRate(scooter=self.vehicle, min_days=2, max_days=6, price_usd=Decimal('12.00'), billing_period_days=1),
            ]
        )

        response = self.client.get(reverse('scooter-detail', args=[self.vehicle.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['pricing_tiers']), 2)

    def test_public_bootstrap_uses_requested_language_for_detail_payload(self):
        VehicleTypeTranslation.objects.create(vehicle_type=self.type, language='ru', name='Скутер')
        VehicleTranslation.objects.create(
            vehicle=self.vehicle,
            language='ru',
            title='Варио 150',
            description='Русское описание',
            rental_terms='Русские условия',
            transmission='Автомат',
            trunk='Багажник 10л',
            color='Чёрный',
        )

        url = reverse('public-bootstrap')
        response = self.client.get(url, {'lang': 'ru'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data['fleet']['items'][0]
        self.assertEqual(item['name'], 'Варио 150')
        self.assertEqual(item['typeLabel'], 'Скутер')
        self.assertEqual(item['description'], 'Русское описание')
        self.assertEqual(item['rentalTerms'], 'Русские условия')
        self.assertEqual(item['features'][0], 'Автомат')
        self.assertEqual(item['features'][2], 'Багажник 10л')
        self.assertEqual(item['specs']['transmission'], 'Автомат')
        self.assertEqual(item['specs']['trunk'], 'Багажник 10л')
        self.assertEqual(item['specs']['color'], 'Чёрный')

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_public_catalog_and_bootstrap_return_relative_media_paths(self):
        image = SimpleUploadedFile('catalog-test.gif', TEST_GIF_BYTES, content_type='image/gif')
        VehicleImage.objects.create(
            vehicle=self.vehicle,
            image=image,
            alt_text='Catalog image',
            is_main=True,
        )

        list_response = self.client.get(reverse('scooter-list'))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertTrue(list_response.data['results'][0]['main_image'].startswith('/media/vehicles/'))

        detail_response = self.client.get(reverse('scooter-detail', args=[self.vehicle.id]))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertTrue(detail_response.data['main_image'].startswith('/media/vehicles/'))
        self.assertTrue(detail_response.data['gallery'][0]['image'].startswith('/media/vehicles/'))

        bootstrap_response = self.client.get(reverse('public-bootstrap'))
        self.assertEqual(bootstrap_response.status_code, status.HTTP_200_OK)
        featured = bootstrap_response.data['fleet']['featured'][0]
        self.assertTrue(featured['mainImage'].startswith('/media/vehicles/'))
        self.assertTrue(featured['gallery'][0]['image'].startswith('/media/vehicles/'))

    def test_public_endpoints_ignore_gallery_rows_without_file(self):
        broken_image = VehicleImage.objects.create(
            vehicle=self.vehicle,
            alt_text='Broken image',
            is_main=True,
        )
        self.assertFalse(bool(broken_image.image))

        list_response = self.client.get(reverse('scooter-list'))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertIsNone(list_response.data['results'][0]['main_image'])

        bootstrap_response = self.client.get(reverse('public-bootstrap'))
        self.assertEqual(bootstrap_response.status_code, status.HTTP_200_OK)
        featured = bootstrap_response.data['fleet']['featured'][0]
        self.assertIsNone(featured['mainImage'])
        self.assertEqual(featured['gallery'], [])

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

    def test_vehicle_type_create_without_code_generates_one(self):
        url = reverse('scooter-type-list')
        self.client.force_authenticate(self.admin_user)
        with patch('catalog.views.vehicle_type_translation_table_available', return_value=False), patch(
            'catalog.serializers.vehicle_type_translation_table_available', return_value=False
        ):
            response = self.client.post(url, {'name': 'Maxi Scooter'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['code'], 'maxi_scooter')
        self.assertTrue(VehicleType.objects.filter(code='maxi_scooter').exists())

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
