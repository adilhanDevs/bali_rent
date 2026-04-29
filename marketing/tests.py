from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.models import Booking
from catalog.models import Vehicle, VehicleModel, VehicleType

from marketing.models import Banner, PromoCode, PromoCodeRedemption, PromotionCampaign
from marketing.services import MarketingService
from loyalty.models import Referral
from loyalty.services.referrals import ReferralService

User = get_user_model()


def banner_upload(name='banner.gif'):
    return SimpleUploadedFile(
        name,
        b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!'
        b'\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00'
        b'\x00\x02\x02D\x01\x00;',
        content_type='image/gif',
    )


class MarketingServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='customer@example.com',
            username='customer',
            password='password123',
            role='client',
        )
        self.now = timezone.now()
        self.campaign = PromotionCampaign.objects.create(
            name='Summer Sale',
            code='summer-sale',
            starts_at=self.now - timedelta(days=1),
            ends_at=self.now + timedelta(days=5),
            is_active=True,
        )

    def test_validate_fixed_discount(self):
        promo = PromoCode.objects.create(
            campaign=self.campaign,
            code='FIXED5',
            discount_type='FIXED',
            discount_value=Decimal('5.00'),
            usage_limit=10,
            is_active=True,
        )
        resolved, discount = MarketingService.validate_promo_code('FIXED5', self.user, Decimal('100.00'))
        self.assertEqual(resolved, promo)
        self.assertEqual(discount, Decimal('5.00'))

    def test_validate_percent_discount_with_cap(self):
        PromoCode.objects.create(
            campaign=self.campaign,
            code='PERCENT10',
            discount_type='PERCENT',
            discount_value=Decimal('10.00'),
            usage_limit=10,
            max_discount_amount=Decimal('5.00'),
            is_active=True,
        )
        _, discount = MarketingService.validate_promo_code('PERCENT10', self.user, Decimal('100.00'))
        self.assertEqual(discount, Decimal('5.00'))

    def test_expired_campaign_invalidates_promo(self):
        expired_campaign = PromotionCampaign.objects.create(
            name='Expired',
            code='expired',
            starts_at=self.now - timedelta(days=5),
            ends_at=self.now - timedelta(days=1),
            is_active=True,
        )
        PromoCode.objects.create(
            campaign=expired_campaign,
            code='EXPIRED',
            discount_type='FIXED',
            discount_value=Decimal('5.00'),
            usage_limit=10,
            is_active=True,
        )
        promo, message = MarketingService.validate_promo_code('EXPIRED', self.user, Decimal('100.00'))
        self.assertIsNone(promo)
        self.assertEqual(message, 'Promo code expired')

    def test_usage_limit_is_checked_using_redemptions(self):
        promo = PromoCode.objects.create(
            campaign=self.campaign,
            code='LIMIT1',
            discount_type='FIXED',
            discount_value=Decimal('5.00'),
            usage_limit=1,
            current_usage=0,
            is_active=True,
        )
        PromoCodeRedemption.objects.create(
            promo_code=promo,
            user=self.user,
            discount_amount=Decimal('5.00'),
        )
        resolved, message = MarketingService.validate_promo_code('LIMIT1', self.user, Decimal('100.00'))
        self.assertIsNone(resolved)
        self.assertEqual(message, 'Promo code usage limit reached')

    def test_apply_promo_code_creates_redemption(self):
        promo = PromoCode.objects.create(
            campaign=self.campaign,
            code='APPLY',
            discount_type='FIXED',
            discount_value=Decimal('7.00'),
            usage_limit=10,
            is_active=True,
        )
        type_obj = VehicleType.objects.create(code='scooter', name='Scooter')
        model = VehicleModel.objects.create(
            name='NMAX',
            brand='Yamaha',
            type=type_obj,
            engine_cc=155,
            transmission='auto',
            fuel_consumption=Decimal('2.20'),
            year=2024,
            trunk='large',
            helmets_count=2,
            description='Test',
            rental_terms='Test',
        )
        vehicle = Vehicle.objects.create(
            model=model,
            title='Yamaha NMAX',
            slug='yamaha-nmax-marketing',
            sku='MRKT001',
            color='Black',
            base_price_usd=Decimal('20.00'),
            status='available',
        )
        booking = Booking.objects.create(
            public_number='BK-MKT-1',
            user=self.user,
            vehicle=vehicle,
            start_at=self.now + timedelta(days=1),
            end_at=self.now + timedelta(days=2),
            payment_method='online_card',
            currency='USD',
            subtotal_usd=Decimal('20.00'),
            discount_usd=Decimal('7.00'),
            total_usd=Decimal('13.00'),
            total_display='USD 13.00',
            status='created',
        )

        redemption = MarketingService.apply_promo_code(
            promo,
            user=self.user,
            booking=booking,
            discount_amount=Decimal('7.00'),
        )
        promo.refresh_from_db()

        self.assertEqual(promo.current_usage, 1)
        self.assertEqual(redemption.promo_code, promo)
        self.assertEqual(redemption.booking, booking)
        self.assertEqual(redemption.discount_amount, Decimal('7.00'))

    def test_referral_creation_uses_shared_idempotent_service(self):
        referred = User.objects.create_user(
            email='referred@example.com',
            username='referred',
            password='password123',
            role='client',
        )

        first = MarketingService.create_referral(self.user, referred)
        second = ReferralService.create_referral(self.user, referred)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Referral.objects.count(), 1)


class MarketingAPITest(APITestCase):
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
        self.client_user = User.objects.create_user(
            email='client@example.com',
            username='client',
            password='password123',
            role='client',
        )
        self.now = timezone.now()
        self.campaign = PromotionCampaign.objects.create(
            name='Launch Campaign',
            code='launch-campaign',
            starts_at=self.now - timedelta(days=1),
            ends_at=self.now + timedelta(days=10),
            is_active=True,
        )
        self.promo = PromoCode.objects.create(
            campaign=self.campaign,
            code='WELCOME10',
            discount_type='PERCENT',
            discount_value=Decimal('10.00'),
            usage_limit=5,
            is_active=True,
        )
        self.banner = Banner.objects.create(
            title='Homepage Banner',
            image=banner_upload(),
            link_url='https://example.com/promo',
            placement='home_top',
            priority=10,
            starts_at=self.now - timedelta(hours=1),
            ends_at=self.now + timedelta(days=1),
            is_active=True,
        )

    def test_public_validate_success(self):
        response = self.client.post(
            reverse('promocode-validate'),
            {'code': 'WELCOME10', 'amount': '100.00'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])
        self.assertEqual(response.data['message'], 'Promo code is valid')
        self.assertEqual(Decimal(response.data['discount']), Decimal('10.00'))
        self.assertEqual(Decimal(response.data['discount_amount']), Decimal('10.00'))

    def test_public_validate_usage_limit_failure(self):
        self.promo.current_usage = 5
        self.promo.save(update_fields=['current_usage'])
        response = self.client.post(
            reverse('promocode-validate'),
            {'code': 'WELCOME10', 'amount': '100.00'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['valid'])
        self.assertEqual(response.data['message'], 'Promo code usage limit reached')
        self.assertEqual(response.data['reason'], 'Promo code usage limit reached')

    def test_booking_create_applies_promo_code_and_creates_redemption(self):
        vehicle_type = VehicleType.objects.create(code='booking-scooter', name='Booking Scooter')
        vehicle_model = VehicleModel.objects.create(
            name='ADV',
            brand='Honda',
            type=vehicle_type,
            engine_cc=160,
            transmission='auto',
            fuel_consumption=Decimal('2.40'),
            year=2024,
            trunk='medium',
            helmets_count=2,
            description='Booking test scooter',
            rental_terms='Terms',
        )
        vehicle = Vehicle.objects.create(
            model=vehicle_model,
            title='Honda ADV',
            slug='honda-adv-discount',
            sku='ADV-DISCOUNT',
            color='Grey',
            base_price_usd=Decimal('20.00'),
            status='available',
        )

        self.client.force_authenticate(user=self.client_user)
        response = self.client.post(
            '/api/v1/bookings/',
            {
                'scooter_id': vehicle.id,
                'start_datetime': (self.now + timedelta(days=2)).isoformat(),
                'end_datetime': (self.now + timedelta(days=3)).isoformat(),
                'payment_method': 'online_card',
                'promo_code': 'WELCOME10',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        booking = Booking.objects.get()
        self.promo.refresh_from_db()

        self.assertEqual(booking.discount_usd, Decimal('2.00'))
        self.assertEqual(self.promo.current_usage, 1)
        redemption = PromoCodeRedemption.objects.get(promo_code=self.promo)
        self.assertEqual(redemption.user, self.client_user)
        self.assertEqual(redemption.booking, booking)
        self.assertEqual(redemption.discount_amount, Decimal('2.00'))

    def test_public_banners_list_returns_only_active_current_banners(self):
        Banner.objects.create(
            title='Expired Banner',
            image=banner_upload('expired.gif'),
            link_url='https://example.com/expired',
            placement='home_top',
            priority=1,
            starts_at=self.now - timedelta(days=3),
            ends_at=self.now - timedelta(days=1),
            is_active=True,
        )

        response = self.client.get(reverse('banner-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Homepage Banner')

    def test_admin_campaign_crud_for_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        create_response = self.client.post(
            reverse('admin-campaign-list'),
            {
                'name': 'Admin Campaign',
                'code': 'admin-campaign',
                'starts_at': (self.now + timedelta(days=1)).isoformat(),
                'ends_at': (self.now + timedelta(days=5)).isoformat(),
                'is_active': True,
                'description': '',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        campaign_id = create_response.data['id']
        patch_response = self.client.patch(
            reverse('admin-campaign-detail', kwargs={'pk': campaign_id}),
            {'name': 'Updated Campaign'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        delete_response = self.client.delete(reverse('admin-campaign-detail', kwargs={'pk': campaign_id}))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_manager_has_full_marketing_admin_access(self):
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.post(
            reverse('admin-promocode-list'),
            {
                'campaign': self.campaign.id,
                'code': 'MANAGER20',
                'discount_type': 'FIXED',
                'discount_value': '20.00',
                'usage_limit': 3,
                'current_usage': 0,
                'starts_at': (self.now - timedelta(days=1)).isoformat(),
                'ends_at': (self.now + timedelta(days=1)).isoformat(),
                'min_booking_amount': '0.00',
                'max_discount_amount': None,
                'is_active': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_staff_is_read_only_for_marketing_admin(self):
        self.client.force_authenticate(user=self.staff_user)

        list_response = self.client.get(reverse('admin-promocode-list'))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            reverse('admin-promocode-list'),
            {
                'campaign': self.campaign.id,
                'code': 'STAFF5',
                'discount_type': 'FIXED',
                'discount_value': '5.00',
                'usage_limit': 1,
                'current_usage': 0,
                'starts_at': (self.now - timedelta(days=1)).isoformat(),
                'ends_at': (self.now + timedelta(days=1)).isoformat(),
                'min_booking_amount': '0.00',
                'max_discount_amount': None,
                'is_active': True,
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_client_cannot_access_marketing_admin(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(reverse('admin-campaign-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
