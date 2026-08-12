from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from bookings.models import Booking
from catalog.models import Vehicle, VehicleModel, VehicleType

from pricing.models import (
    DevicePricingRule,
    GeoPricingRule,
    OccupancyPricingRule,
    PriceCalculationLog,
    ScooterRentalRate,
    ScooterSeasonPrice,
    Season,
)
from pricing.services import PricingCalculationService

User = get_user_model()


class PricingCalculationServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='customer@example.com',
            username='customer',
            password='password123',
        )
        self.vehicle_type = VehicleType.objects.create(code='scooter', name='Scooter')
        self.vehicle_model = VehicleModel.objects.create(
            name='NMAX',
            brand='Yamaha',
            type=self.vehicle_type,
            engine_cc=155,
            transmission='auto',
            fuel_consumption=Decimal('2.50'),
            year=2024,
            trunk='large',
            helmets_count=2,
            description='Comfort scooter',
            rental_terms='Passport required',
        )
        self.vehicle = Vehicle.objects.create(
            model=self.vehicle_model,
            title='Yamaha NMAX',
            slug='yamaha-nmax',
            sku='NMAX001',
            color='Black',
            base_price_usd=Decimal('20.00'),
            status='available',
        )

    def test_base_price_only(self):
        start_date = timezone.localdate() + timedelta(days=1)
        end_date = start_date + timedelta(days=2)

        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_date,
            end_at=end_date,
        )

        self.assertEqual(result['base_price'], Decimal('40.00'))
        self.assertEqual(result['season_adjustment'], Decimal('0.00'))
        self.assertEqual(result['occupancy_adjustment'], Decimal('0.00'))
        self.assertEqual(result['device_adjustment'], Decimal('0.00'))
        self.assertEqual(result['geo_adjustment'], Decimal('0.00'))
        self.assertEqual(result['final_total'], Decimal('40.00'))

    def test_pickup_before_18_counts_start_day_but_18_does_not(self):
        start_date = timezone.localdate() + timedelta(days=1)
        return_date = start_date + timedelta(days=1)
        before_cutoff = timezone.make_aware(datetime.combine(start_date, time(17, 59)))
        at_cutoff = timezone.make_aware(datetime.combine(start_date, time(18, 0)))
        return_at = timezone.make_aware(datetime.combine(return_date, time(18, 0)))

        self.assertEqual(PricingCalculationService.calculate_rental_days(before_cutoff, return_at), 2)
        self.assertEqual(PricingCalculationService.calculate_rental_days(at_cutoff, return_at), 1)

    def test_season_override_and_multiplier(self):
        start_date = timezone.localdate() + timedelta(days=3)
        end_date = start_date + timedelta(days=2)
        season = Season.objects.create(
            name='High Season',
            code='high-season',
            start_date=start_date - timedelta(days=1),
            end_date=end_date + timedelta(days=1),
            multiplier=Decimal('1.50'),
            is_active=True,
        )
        ScooterSeasonPrice.objects.create(
            scooter=self.vehicle,
            season=season,
            price_per_day_usd=Decimal('25.00'),
        )

        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_date,
            end_at=end_date,
        )

        self.assertEqual(result['base_price'], Decimal('40.00'))
        self.assertEqual(result['season_adjustment'], Decimal('35.00'))
        self.assertEqual(result['final_total'], Decimal('75.00'))

    def test_occupancy_device_and_geo_adjustments(self):
        second_vehicle = Vehicle.objects.create(
            model=self.vehicle_model,
            title='Yamaha NMAX 2',
            slug='yamaha-nmax-2',
            sku='NMAX002',
            color='Blue',
            base_price_usd=Decimal('20.00'),
            status='available',
        )
        start_date = timezone.localdate() + timedelta(days=5)
        end_date = start_date + timedelta(days=1)

        Booking.objects.create(
            public_number='BK-OCC-1',
            user=self.user,
            vehicle=second_vehicle,
            start_at=timezone.make_aware(datetime.combine(start_date, time.min)),
            end_at=timezone.make_aware(datetime.combine(end_date, time.min)),
            payment_method='online_card',
            currency='USD',
            subtotal_usd=Decimal('20.00'),
            total_usd=Decimal('20.00'),
            total_display='USD 20.00',
            status='confirmed',
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
            multiplier=Decimal('0.90'),
            is_active=True,
        )

        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_date,
            end_at=end_date,
            device_platform='ios',
            user_country='ID',
        )

        self.assertEqual(result['base_price'], Decimal('20.00'))
        self.assertEqual(result['occupancy_adjustment'], Decimal('2.00'))
        self.assertEqual(result['device_adjustment'], Decimal('1.10'))
        self.assertEqual(result['geo_adjustment'], Decimal('-2.31'))
        self.assertEqual(result['final_total'], Decimal('20.79'))

    def test_low_availability_applies_default_twenty_percent_markup(self):
        additional_vehicles = [
            Vehicle.objects.create(
                model=self.vehicle_model,
                title=f'Yamaha NMAX {index}',
                slug=f'yamaha-nmax-{index}',
                sku=f'NMAX00{index}',
                color='Blue',
                base_price_usd=Decimal('20.00'),
                status='available',
            )
            for index in range(2, 7)
        ]
        start_date = timezone.localdate() + timedelta(days=7)
        end_date = start_date + timedelta(days=1)

        for index, vehicle in enumerate(additional_vehicles, start=1):
            Booking.objects.create(
                public_number=f'BK-LOW-{index}',
                user=self.user,
                vehicle=vehicle,
                start_at=timezone.make_aware(datetime.combine(start_date, time.min)),
                end_at=timezone.make_aware(datetime.combine(end_date, time.min)),
                payment_method='online_card',
                currency='USD',
                subtotal_usd=Decimal('20.00'),
                total_usd=Decimal('20.00'),
                total_display='USD 20.00',
                status='confirmed',
            )

        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_date,
            end_at=end_date,
        )

        self.assertEqual(result['base_price'], Decimal('20.00'))
        self.assertEqual(result['occupancy_adjustment'], Decimal('4.00'))
        self.assertEqual(result['final_total'], Decimal('24.00'))
        self.assertEqual(result['pricing_snapshot']['rules']['availability_percent'], 17)
        self.assertEqual(result['pricing_snapshot']['rules']['occupancy_rule_source'], 'default_low_availability')

    def test_price_calculation_log_is_saved(self):
        start_date = timezone.localdate() + timedelta(days=1)
        end_date = start_date + timedelta(days=1)

        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_date,
            end_at=end_date,
            user=self.user,
        )

        log = PriceCalculationLog.objects.get(pk=result['price_calculation_id'])
        self.assertEqual(log.scooter, self.vehicle)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.base_price, Decimal('20.00'))
        self.assertEqual(log.final_price, Decimal('20.00'))
        self.assertEqual(log.payload_json['breakdown']['final_total'], '20.00')

    def test_duration_rate_range_is_applied(self):
        ScooterRentalRate.objects.bulk_create(
            [
                ScooterRentalRate(scooter=self.vehicle, min_days=1, max_days=1, price_usd=Decimal('20.00'), billing_period_days=1),
                ScooterRentalRate(scooter=self.vehicle, min_days=2, max_days=6, price_usd=Decimal('18.00'), billing_period_days=1),
                ScooterRentalRate(scooter=self.vehicle, min_days=7, max_days=15, price_usd=Decimal('15.00'), billing_period_days=1),
            ]
        )
        start_date = timezone.localdate() + timedelta(days=1)
        end_date = start_date + timedelta(days=4)

        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_date,
            end_at=end_date,
        )

        self.assertEqual(result['base_price'], Decimal('72.00'))
        self.assertEqual(result['final_total'], Decimal('72.00'))
        self.assertEqual(result['applied_tariff']['min_days'], 2)
        self.assertEqual(result['applied_tariff']['max_days'], 6)
        self.assertEqual(result['applied_tariff']['billing_period_days'], 1)

    def test_monthly_duration_rate_combines_full_months_with_daily_remainder(self):
        ScooterRentalRate.objects.bulk_create(
            [
                ScooterRentalRate(scooter=self.vehicle, min_days=1, max_days=29, price_usd=Decimal('20.00'), billing_period_days=1),
                ScooterRentalRate(scooter=self.vehicle, min_days=30, max_days=None, price_usd=Decimal('180.00'), billing_period_days=30),
            ]
        )
        start_date = timezone.localdate() + timedelta(days=1)
        end_date = start_date + timedelta(days=35)

        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_date,
            end_at=end_date,
        )

        self.assertEqual(result['base_price'], Decimal('280.00'))
        self.assertEqual(result['final_total'], Decimal('280.00'))
        self.assertEqual(result['applied_tariff']['billing_period_days'], 30)
        self.assertEqual(result['applied_tariff']['billed_periods'], 1)
        self.assertEqual(result['applied_tariff']['remainder_days'], 5)

    def test_exact_month_range_still_applies_to_32_days_plus_daily_remainder(self):
        ScooterRentalRate.objects.bulk_create(
            [
                ScooterRentalRate(scooter=self.vehicle, min_days=1, max_days=1, price_usd=Decimal('20.00'), billing_period_days=1),
                ScooterRentalRate(scooter=self.vehicle, min_days=2, max_days=6, price_usd=Decimal('18.00'), billing_period_days=1),
                ScooterRentalRate(scooter=self.vehicle, min_days=30, max_days=30, price_usd=Decimal('180.00'), billing_period_days=30),
            ]
        )
        start_date = timezone.localdate() + timedelta(days=1)

        result = PricingCalculationService.calculate_full_price(
            vehicle_id=self.vehicle.id,
            start_at=start_date,
            end_at=start_date + timedelta(days=32),
        )

        self.assertEqual(result['base_price'], Decimal('216.00'))
        self.assertEqual(result['applied_tariff']['billing_period_days'], 30)
        self.assertEqual(result['applied_tariff']['billed_periods'], 1)
        self.assertEqual(result['applied_tariff']['remainder_days'], 2)
