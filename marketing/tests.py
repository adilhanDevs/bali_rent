from django.test import TestCase
from decimal import Decimal
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from marketing.models import PromoCode, PromotionCampaign
from marketing.services import MarketingService
from datetime import timedelta
from django.contrib.auth import get_user_model

User = get_user_model()

class MarketingServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', username='test', password='password')
        self.now = timezone.now()

    def test_valid_promocode_fixed(self):
        promo = PromoCode.objects.create(
            code='FIXED5',
            discount_type='FIXED',
            value=Decimal('5.00'),
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=1),
            is_active=True
        )
        p, discount = MarketingService.validate_promo_code('FIXED5', self.user, Decimal('100.00'))
        self.assertEqual(p, promo)
        self.assertEqual(discount, Decimal('5.00'))

    def test_valid_promocode_percent_with_cap(self):
        promo = PromoCode.objects.create(
            code='PERCENT10',
            discount_type='PERCENT',
            value=Decimal('10.00'),
            max_discount_amount=Decimal('5.00'),
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=1),
            is_active=True
        )
        # 10% of 100 is 10, but capped at 5
        p, discount = MarketingService.validate_promo_code('PERCENT10', self.user, Decimal('100.00'))
        self.assertEqual(discount, Decimal('5.00'))
        
        # 10% of 20 is 2, not capped
        p, discount = MarketingService.validate_promo_code('PERCENT10', self.user, Decimal('20.00'))
        self.assertEqual(discount, Decimal('2.00'))

    def test_expired_promocode(self):
        PromoCode.objects.create(
            code='EXPIRED',
            discount_type='FIXED',
            value=Decimal('5.00'),
            valid_from=self.now - timedelta(days=2),
            valid_until=self.now - timedelta(days=1),
            is_active=True
        )
        p, msg = MarketingService.validate_promo_code('EXPIRED', self.user, Decimal('100.00'))
        self.assertIsNone(p)
        self.assertEqual(msg, "Promo code expired")

    def test_future_promocode(self):
        PromoCode.objects.create(
            code='FUTURE',
            discount_type='FIXED',
            value=Decimal('5.00'),
            valid_from=self.now + timedelta(days=1),
            valid_until=self.now + timedelta(days=2),
            is_active=True
        )
        p, msg = MarketingService.validate_promo_code('FUTURE', self.user, Decimal('100.00'))
        self.assertIsNone(p)
        self.assertEqual(msg, "Promo code is not yet valid")

    def test_usage_limit_exceeded(self):
        promo = PromoCode.objects.create(
            code='LIMIT1',
            discount_type='FIXED',
            value=Decimal('5.00'),
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=1),
            usage_limit=1,
            current_usage=1,
            is_active=True
        )
        p, msg = MarketingService.validate_promo_code('LIMIT1', self.user, Decimal('100.00'))
        self.assertIsNone(p)
        self.assertEqual(msg, "Promo code usage limit reached")

    def test_inactive_promocode(self):
        PromoCode.objects.create(
            code='INACTIVE',
            discount_type='FIXED',
            value=Decimal('5.00'),
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=1),
            is_active=False
        )
        p, msg = MarketingService.validate_promo_code('INACTIVE', self.user, Decimal('100.00'))
        self.assertIsNone(p)
        self.assertEqual(msg, "Promo code is inactive")

class MarketingAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', username='test', password='password', role='client')
        self.admin = User.objects.create_superuser(email='admin@example.com', username='admin', password='password', role='admin')
        self.now = timezone.now()
        self.validate_url = reverse('promocode-validate')

    def test_public_validate_success(self):
        PromoCode.objects.create(
            code='WELCOME',
            discount_type='PERCENT',
            value=Decimal('10.00'),
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=1),
            is_active=True
        )
        data = {"code": "WELCOME", "amount": "100.00"}
        response = self.client.post(self.validate_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])
        self.assertEqual(Decimal(response.data['discount_amount']), Decimal('10.00'))

    def test_admin_access_protection(self):
        url = reverse('admin-campaign-list')
        
        # Unauthorized
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Client
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Admin
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
