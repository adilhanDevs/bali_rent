from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.models import Booking
from bookings.services import BookingCreationService, BookingPriceService
from catalog.models import Vehicle, VehicleModel, VehicleType

from .models import PaymentMethodAdjustment
from .services import PaymentAdjustmentService

User = get_user_model()


class PaymentAdjustmentServiceTest(TestCase):
    def test_default_adjustments_are_applied(self):
        online = PaymentAdjustmentService.apply_adjustment(Decimal('100.00'), 'online_card')
        cash = PaymentAdjustmentService.apply_adjustment(Decimal('100.00'), 'cash_on_delivery')
        card = PaymentAdjustmentService.apply_adjustment(Decimal('100.00'), 'card_on_delivery')

        self.assertEqual(online['adjusted_total_usd'], Decimal('100.00'))
        self.assertEqual(cash['adjusted_total_usd'], Decimal('90.00'))
        self.assertEqual(cash['discount_usd'], Decimal('10.00'))
        self.assertEqual(card['adjusted_total_usd'], Decimal('110.00'))
        self.assertEqual(card['markup_usd'], Decimal('10.00'))

    def test_admin_config_overrides_defaults(self):
        PaymentMethodAdjustment.objects.update_or_create(
            payment_method='cash_on_delivery',
            defaults={
                'adjustment_percent': Decimal('-15.00'),
                'is_active': True,
            },
        )
        PaymentMethodAdjustment.objects.update_or_create(
            payment_method='card_on_delivery',
            defaults={
                'adjustment_percent': Decimal('7.50'),
                'is_active': True,
            },
        )

        cash = PaymentAdjustmentService.apply_adjustment(Decimal('200.00'), 'cash_on_delivery')
        card = PaymentAdjustmentService.apply_adjustment(Decimal('200.00'), 'card_on_delivery')

        self.assertEqual(cash['adjusted_total_usd'], Decimal('170.00'))
        self.assertEqual(cash['discount_usd'], Decimal('30.00'))
        self.assertEqual(card['adjusted_total_usd'], Decimal('215.00'))
        self.assertEqual(card['markup_usd'], Decimal('15.00'))


class PaymentBookingIntegrationTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='customer@example.com',
            username='customer',
            password='password123',
            role='client',
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
            description='Test scooter',
            rental_terms='Test rental terms',
        )
        self.vehicle = Vehicle.objects.create(
            model=self.vehicle_model,
            title='Yamaha NMAX',
            slug='yamaha-nmax-payments',
            sku='PAY001',
            color='Black',
            base_price_usd=Decimal('20.00'),
            status='available',
        )

    def test_booking_calculate_uses_default_cash_and_card_adjustments(self):
        start_at = timezone.now() + timedelta(days=1)
        end_at = timezone.now() + timedelta(days=2)

        cash_result = BookingPriceService.calculate_prices(
            vehicle=self.vehicle,
            start_at=start_at,
            end_at=end_at,
            payment_method='cash_on_delivery',
        )
        card_result = BookingPriceService.calculate_prices(
            vehicle=self.vehicle,
            start_at=start_at,
            end_at=end_at,
            payment_method='card_on_delivery',
        )

        self.assertEqual(cash_result['total_usd'], Decimal('18.00'))
        self.assertEqual(cash_result['discount_usd'], Decimal('2.00'))
        self.assertEqual(card_result['total_usd'], Decimal('22.00'))
        self.assertEqual(card_result['markup_usd'], Decimal('2.00'))

    def test_booking_creation_uses_admin_adjustment_settings(self):
        PaymentMethodAdjustment.objects.update_or_create(
            payment_method='cash_on_delivery',
            defaults={
                'adjustment_percent': Decimal('-15.00'),
                'is_active': True,
            },
        )

        booking = BookingCreationService.create_booking(
            user=self.user,
            vehicle_id=self.vehicle.id,
            start_at=timezone.now() + timedelta(days=3),
            end_at=timezone.now() + timedelta(days=4),
            payment_method='cash_on_delivery',
            currency='USD',
        )

        self.assertEqual(booking.total_usd, Decimal('17.00'))
        self.assertEqual(booking.discount_usd, Decimal('3.00'))
        self.assertEqual(booking.markup_usd, Decimal('0.00'))
        self.assertEqual(Booking.objects.count(), 1)
