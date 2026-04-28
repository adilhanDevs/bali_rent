from django.test import TestCase
from decimal import Decimal
from django.utils import timezone
from catalog.models import Vehicle, VehicleModel, VehicleType
from addons.models import Addon
from marketing.models import PromoCode
from pricing.models import (
    Season, ScooterSeasonPrice, OccupancyPricingRule, 
    DevicePricingRule, GeoPricingRule, PriceCalculationLog
)
from pricing.services import PricingCalculationService
from datetime import timedelta
from django.contrib.auth import get_user_model

User = get_user_model()

class PricingCalculationServiceTest(TestCase):
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
        self.user = User.objects.create_user(email='test@example.com', username='test', password='password')

    def test_base_price_only(self):
        start_at = timezone.now() + timedelta(days=1)
        end_at = start_at + timedelta(days=1)
        
        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_at,
            end_at=end_at
        )
        
        self.assertEqual(result['final_price'], Decimal('20.00'))

    def test_season_multiplier(self):
        start_at = timezone.now() + timedelta(days=1)
        end_at = start_at + timedelta(days=1)
        
        season = Season.objects.create(
            name='High Season',
            start_date=start_at.date() - timedelta(days=1),
            end_date=start_at.date() + timedelta(days=1),
            is_active=True
        )
        ScooterSeasonPrice.objects.create(
            scooter=self.vehicle,
            season=season,
            price_per_day=Decimal('30.00')
        )
        
        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_at,
            end_at=end_at
        )
        
        self.assertEqual(result['final_price'], Decimal('30.00'))

    def test_occupancy_rule(self):
        # Create another vehicle to make occupancy calculation more interesting
        Vehicle.objects.create(
            model=self.vm, title='Yamaha NMAX 2', slug='nmax-2', sku='NMAX002',
            color='Black', base_price_usd=Decimal('20.00'), status='available'
        )
        
        # 0% occupancy by default. Let's add a rule for 0-10% occupancy
        OccupancyPricingRule.objects.create(
            name='Low occupancy discount',
            min_occupancy_percent=0,
            max_occupancy_percent=10,
            adjustment_percent=Decimal('-10.00'), # 10% discount
            is_active=True
        )
        
        start_at = timezone.now() + timedelta(days=1)
        end_at = start_at + timedelta(days=1)
        
        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_at,
            end_at=end_at
        )
        
        # 20 - 10% = 18
        self.assertEqual(result['final_price'], Decimal('18.00'))

    def test_device_rule(self):
        DevicePricingRule.objects.create(
            name='iOS Surcharge',
            platform='ios',
            adjustment_percent=Decimal('5.00'),
            is_active=True
        )
        
        start_at = timezone.now() + timedelta(days=1)
        end_at = start_at + timedelta(days=1)
        
        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_at,
            end_at=end_at,
            device_platform='ios'
        )
        
        # 20 + 5% = 21
        self.assertEqual(result['final_price'], Decimal('21.00'))

    def test_geo_rule(self):
        GeoPricingRule.objects.create(
            name='Local Discount',
            country_code='ID',
            adjustment_percent=Decimal('-20.00'),
            is_active=True
        )
        
        start_at = timezone.now() + timedelta(days=1)
        end_at = start_at + timedelta(days=1)
        
        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_at,
            end_at=end_at,
            user_country='ID'
        )
        
        # 20 - 20% = 16
        self.assertEqual(result['final_price'], Decimal('16.00'))

    def test_addons(self):
        addon = Addon.objects.create(
            code='helmet_extra', name='Extra Helmet', price_usd=Decimal('5.00'), 
            price_type='per_booking', is_active=True
        )
        
        start_at = timezone.now() + timedelta(days=1)
        end_at = start_at + timedelta(days=1)
        
        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_at,
            end_at=end_at,
            addon_ids=[addon.id]
        )
        
        # 20 + 5 = 25
        self.assertEqual(result['final_price'], Decimal('25.00'))
        self.assertEqual(result['addons_total'], Decimal('5.00'))

    def test_promocode_discount(self):
        PromoCode.objects.create(
            code='WELCOME',
            discount_type='FIXED',
            value=Decimal('5.00'),
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=1),
            usage_limit=100,
            is_active=True
        )
        
        start_at = timezone.now() + timedelta(days=1)
        end_at = start_at + timedelta(days=1)
        
        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_at,
            end_at=end_at,
            promo_code='WELCOME',
            user=self.user
        )
        
        # 20 - 5 = 15
        self.assertEqual(result['final_price'], Decimal('15.00'))
        self.assertEqual(result['discount_amount'], Decimal('5.00'))

    def test_snapshot_creation(self):
        start_at = timezone.now() + timedelta(days=1)
        end_at = start_at + timedelta(days=1)
        
        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_at,
            end_at=end_at
        )
        
        log = PriceCalculationLog.objects.get(id=result['price_calculation_id'])
        self.assertIsNotNone(log.calculation_snapshot)
        self.assertEqual(log.total_price, Decimal('20.00'))
        self.assertTrue(any(step['step'] == 'base_price' for step in log.calculation_snapshot['steps']))
