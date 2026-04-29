from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.models import Booking
from catalog.models import Vehicle, VehicleModel, VehicleType

from pricing.models import (
    DevicePricingRule,
    GeoPricingRule,
    OccupancyPricingRule,
    PriceCalculationLog,
    ScooterSeasonPrice,
    Season,
)

User = get_user_model()


class PricingAPITest(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            username='admin',
            password='password123',
            role='admin',
        )
        self.manager_user = User.objects.create_user(
            email='manager@example.com',
            username='manager',
            password='password123',
            role='manager',
        )
        self.staff_user = User.objects.create_user(
            email='staff@example.com',
            username='staff',
            password='password123',
            role='staff',
        )
        self.customer_user = User.objects.create_user(
            email='customer@example.com',
            username='customer',
            password='password123',
            role='client',
        )

        self.vehicle_type = VehicleType.objects.create(code='scooter', name='Scooter')
        self.vehicle_model = VehicleModel.objects.create(
            name='PCX',
            brand='Honda',
            type=self.vehicle_type,
            engine_cc=160,
            transmission='auto',
            fuel_consumption=Decimal('2.30'),
            year=2024,
            trunk='medium',
            helmets_count=2,
            description='City scooter',
            rental_terms='Valid ID required',
        )
        self.vehicle = Vehicle.objects.create(
            model=self.vehicle_model,
            title='Honda PCX',
            slug='honda-pcx',
            sku='PCX001',
            color='White',
            base_price_usd=Decimal('20.00'),
            status='available',
        )
        self.other_vehicle = Vehicle.objects.create(
            model=self.vehicle_model,
            title='Honda PCX 2',
            slug='honda-pcx-2',
            sku='PCX002',
            color='Red',
            base_price_usd=Decimal('20.00'),
            status='available',
        )

        self.calculate_url = reverse('pricing-calculate')
        self.season_list_url = reverse('admin-season-list')

    def test_calculate_returns_dynamic_breakdown_and_log(self):
        start_date = timezone.localdate() + timedelta(days=2)
        end_date = start_date + timedelta(days=2)

        Season.objects.create(
            name='Peak',
            code='peak',
            start_date=start_date - timedelta(days=1),
            end_date=end_date + timedelta(days=1),
            multiplier=Decimal('1.20'),
            is_active=True,
        )
        ScooterSeasonPrice.objects.create(
            scooter=self.vehicle,
            season=Season.objects.get(code='peak'),
            price_per_day_usd=Decimal('25.00'),
        )
        OccupancyPricingRule.objects.create(
            threshold_percent=50,
            price_increase_percent=Decimal('10.00'),
            is_active=True,
        )
        DevicePricingRule.objects.create(
            device_type='ios',
            country_code='ID',
            multiplier=Decimal('1.05'),
            is_active=True,
        )
        GeoPricingRule.objects.create(
            country_code='ID',
            city='',
            multiplier=Decimal('0.95'),
            is_active=True,
        )
        Booking.objects.create(
            public_number='BK-P-1',
            user=self.customer_user,
            vehicle=self.other_vehicle,
            start_at=timezone.make_aware(datetime.combine(start_date, time.min)),
            end_at=timezone.make_aware(datetime.combine(end_date, time.min)),
            payment_method='online_card',
            currency='USD',
            subtotal_usd=Decimal('40.00'),
            total_usd=Decimal('40.00'),
            total_display='USD 40.00',
            status='confirmed',
        )

        response = self.client.post(
            self.calculate_url,
            {
                'scooter_id': self.vehicle.id,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'device_type': 'ios',
                'country_code': 'ID',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['base_price']), Decimal('40.00'))
        self.assertEqual(Decimal(response.data['season_adjustment']), Decimal('20.00'))
        self.assertEqual(Decimal(response.data['occupancy_adjustment']), Decimal('6.00'))
        self.assertEqual(Decimal(response.data['device_adjustment']), Decimal('3.30'))
        self.assertEqual(Decimal(response.data['geo_adjustment']), Decimal('-3.47'))
        self.assertEqual(Decimal(response.data['final_total']), Decimal('65.83'))
        self.assertTrue(PriceCalculationLog.objects.filter(pk=response.data['price_calculation_id']).exists())

    def test_calculate_validation_errors(self):
        response = self.client.post(
            self.calculate_url,
            {
                'scooter_id': self.vehicle.id,
                'start_date': '2026-06-10',
                'end_date': '2026-06-09',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('end_date', response.data)

    def test_calculate_supports_legacy_aliases(self):
        response = self.client.post(
            self.calculate_url,
            {
                'vehicle_id': self.vehicle.id,
                'start_at': (timezone.now() + timedelta(days=1)).isoformat(),
                'end_at': (timezone.now() + timedelta(days=2)).isoformat(),
                'device_platform': 'web',
                'user_country': 'US',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('final_total', response.data)

    def test_admin_can_create_and_list_seasons(self):
        self.client.force_authenticate(user=self.admin_user)
        create_response = self.client.post(
            self.season_list_url,
            {
                'name': 'Low Season',
                'code': 'low-season',
                'start_date': '2026-09-01',
                'end_date': '2026-10-01',
                'multiplier': '0.95',
                'is_active': True,
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get(self.season_list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)

    def test_manager_has_full_admin_access(self):
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.post(
            self.season_list_url,
            {
                'name': 'Manager Season',
                'code': 'manager-season',
                'start_date': '2026-07-01',
                'end_date': '2026-07-31',
                'multiplier': '1.10',
                'is_active': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_staff_is_read_only_for_admin_pricing(self):
        season = Season.objects.create(
            name='Existing Season',
            code='existing-season',
            start_date='2026-07-01',
            end_date='2026-07-31',
            multiplier=Decimal('1.00'),
            is_active=True,
        )
        self.client.force_authenticate(user=self.staff_user)

        list_response = self.client.get(self.season_list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            self.season_list_url,
            {
                'name': 'Forbidden Season',
                'code': 'forbidden-season',
                'start_date': '2026-08-01',
                'end_date': '2026-08-31',
                'multiplier': '1.10',
                'is_active': True,
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

        detail_response = self.client.patch(
            reverse('admin-season-detail', kwargs={'pk': season.pk}),
            {'multiplier': '1.20'},
            format='json',
        )
        self.assertEqual(detail_response.status_code, status.HTTP_403_FORBIDDEN)
