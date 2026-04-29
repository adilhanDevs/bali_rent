from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from catalog.models import Vehicle, VehicleType, VehicleModel
from addons.models import Addon
from delivery.models import DeliveryZone
from bookings.models import Booking, AvailabilityBlock
from marketing.models import PromoCode, PromotionCampaign
from datetime import timedelta
from decimal import Decimal

User = get_user_model()

class BookingAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='password', username='testuser')
        self.other_user = User.objects.create_user(email='other@example.com', password='password', username='otheruser')
        self.admin = User.objects.create_superuser(email='admin@example.com', password='password', username='adminuser', role='admin')
        
        self.vt = VehicleType.objects.create(code='scooter', name='Scooter')
        self.vm = VehicleModel.objects.create(
            name='NMAX', brand='Yamaha', type=self.vt, engine_cc=155, 
            transmission='auto', fuel_consumption=2.5, year=2023, 
            trunk='large', helmets_count=2, description='test', rental_terms='test'
        )
        self.vehicle = Vehicle.objects.create(
            model=self.vm, title='Yamaha NMAX 2023', slug='nmax-2023', 
            sku='NMAX001', color='black', base_price_usd=Decimal('20.00'), status='available'
        )
        
        self.addon = Addon.objects.create(
            code='helmet', name='Extra Helmet', description='test', 
            price_usd=Decimal('5.00'), price_type='per_booking', is_active=True
        )
        
        self.zone = DeliveryZone.objects.create(
            name='Canggu', center_lat=-8.65, center_lng=115.13, radius_km=10,
            free_delivery=False, base_price_usd=Decimal('5.00'), price_per_km_usd=Decimal('1.00'), is_active=True
        )
        self.campaign = PromotionCampaign.objects.create(
            name='Booking Campaign',
            code='booking-campaign',
            starts_at=timezone.now() - timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=10),
            is_active=True,
        )
        self.promo = PromoCode.objects.create(
            campaign=self.campaign,
            code='BOOK10',
            discount_type='PERCENT',
            discount_value=Decimal('10.00'),
            usage_limit=5,
            is_active=True,
        )

    def test_calculate_price(self):
        url = '/api/v1/bookings/calculate/'
        data = {
            "scooter_id": self.vehicle.id,
            "start_datetime": (timezone.now() + timedelta(days=1)).isoformat(),
            "end_datetime": (timezone.now() + timedelta(days=5)).isoformat(),
            "delivery_address": "Canggu",
            "delivery_latitude": -8.65,
            "delivery_longitude": 115.13,
            "add_on_ids": [self.addon.id],
            "payment_method": "online_card",
            "currency": "USD"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 4 days * 20.00 = 80.00
        # Addon = 5.00
        # Delivery = 5.00 + 1.0 * 0 = 5.00 (dist is 0)
        # Total = 90.00
        self.assertEqual(Decimal(response.data['total_price']), Decimal('90.00'))

    def test_cash_discount(self):
        url = '/api/v1/bookings/calculate/'
        data = {
            "scooter_id": self.vehicle.id,
            "start_datetime": (timezone.now() + timedelta(days=1)).isoformat(),
            "end_datetime": (timezone.now() + timedelta(days=2)).isoformat(),
            "payment_method": "cash_on_delivery",
        }
        response = self.client.post(url, data)
        # 1 day * 20.00 = 20.00
        # 10% discount = 2.00
        # Total = 18.00
        self.assertEqual(Decimal(response.data['total_price']), Decimal('18.00'))
        self.assertEqual(Decimal(response.data['discount_amount']), Decimal('2.00'))

    def test_calculate_with_promo_code(self):
        url = '/api/v1/bookings/calculate/'
        data = {
            "scooter_id": self.vehicle.id,
            "start_datetime": (timezone.now() + timedelta(days=1)).isoformat(),
            "end_datetime": (timezone.now() + timedelta(days=2)).isoformat(),
            "payment_method": "online_card",
            "promo_code": "BOOK10",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['promo_code'], 'BOOK10')
        self.assertEqual(Decimal(response.data['discount_amount']), Decimal('2.00'))
        self.assertEqual(Decimal(response.data['total_price']), Decimal('18.00'))

    def test_card_markup(self):
        url = '/api/v1/bookings/calculate/'
        data = {
            "scooter_id": self.vehicle.id,
            "start_datetime": (timezone.now() + timedelta(days=1)).isoformat(),
            "end_datetime": (timezone.now() + timedelta(days=2)).isoformat(),
            "payment_method": "card_on_delivery",
        }
        response = self.client.post(url, data)
        # 1 day * 20.00 = 20.00
        # 10% markup = 2.00
        # Total = 22.00
        self.assertEqual(Decimal(response.data['total_price']), Decimal('22.00'))
        self.assertEqual(Decimal(response.data['markup_amount']), Decimal('2.00'))

    def test_create_booking(self):
        self.client.force_authenticate(user=self.user)
        url = '/api/v1/bookings/'
        data = {
            "scooter_id": self.vehicle.id,
            "start_datetime": (timezone.now() + timedelta(days=10)).isoformat(),
            "end_datetime": (timezone.now() + timedelta(days=12)).isoformat(),
            "payment_method": "online_card"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(AvailabilityBlock.objects.count(), 1)
        booking = Booking.objects.get()
        self.assertIn('breakdown', booking.pricing_snapshot_json)
        self.assertIn('booking_totals', booking.pricing_snapshot_json)
        self.assertEqual(Decimal(str(booking.pricing_snapshot_json['booking_totals']['total_usd'])), booking.total_usd)
        self.assertEqual(Decimal(str(booking.pricing_snapshot_json['breakdown']['base_price'])), Decimal('40.00'))

    def test_overlapping_booking_denied(self):
        # Create first booking
        start = timezone.now() + timedelta(days=20)
        end = timezone.now() + timedelta(days=22)
        Booking.objects.create(
            public_number='BK-EXISTING', user=self.user, vehicle=self.vehicle,
            start_at=start, end_at=end, subtotal_usd=40, total_usd=40, status='created'
        )
        AvailabilityBlock.objects.create(
            vehicle=self.vehicle, start_at=start, end_at=end, type='booking'
        )
        
        self.client.force_authenticate(user=self.user)
        url = '/api/v1/bookings/'
        data = {
            "scooter_id": self.vehicle.id,
            "start_datetime": (start + timedelta(hours=1)).isoformat(),
            "end_datetime": (end + timedelta(hours=1)).isoformat(),
            "payment_method": "online_card"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_owner_list_only(self):
        # Create booking for self.user
        Booking.objects.create(
            public_number='BK-USER', user=self.user, vehicle=self.vehicle,
            start_at=timezone.now(), end_at=timezone.now()+timedelta(days=1),
            subtotal_usd=20, total_usd=20, status='created'
        )
        # Create booking for self.other_user
        Booking.objects.create(
            public_number='BK-OTHER', user=self.other_user, vehicle=self.vehicle,
            start_at=timezone.now()+timedelta(days=5), end_at=timezone.now()+timedelta(days=6),
            subtotal_usd=20, total_usd=20, status='created'
        )
        
        self.client.force_authenticate(user=self.user)
        url = '/api/v1/bookings/'
        response = self.client.get(url)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['order_number'], 'BK-USER')

    def test_cancel_booking(self):
        booking = Booking.objects.create(
            public_number='BK-CANCEL', user=self.user, vehicle=self.vehicle,
            start_at=timezone.now()+timedelta(days=30), end_at=timezone.now()+timedelta(days=31),
            subtotal_usd=20, total_usd=20, status='created'
        )
        AvailabilityBlock.objects.create(
            vehicle=self.vehicle, start_at=booking.start_at, end_at=booking.end_at, 
            type='booking', source_booking=booking
        )
        
        self.client.force_authenticate(user=self.user)
        url = f'/api/v1/bookings/{booking.id}/cancel/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')
        self.assertFalse(AvailabilityBlock.objects.filter(source_booking=booking).exists())
