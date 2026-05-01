from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import CryptoCurrency, CryptoInvoice, CryptoWebhookEvent
from .services import CryptoPaymentService
from bookings.models import Booking
from catalog.models import Vehicle, VehicleModel, VehicleType
from users.models import User
from audit.models import WebhookProcessingLog
from decimal import Decimal
from datetime import timedelta
import json

class CryptoPaymentServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', username='test', password='password')
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
        self.booking = Booking.objects.create(
            public_number='BK-123',
            user=self.user,
            vehicle=self.vehicle,
            start_at=timezone.now() + timedelta(days=1),
            end_at=timezone.now() + timedelta(days=2),
            subtotal_usd=Decimal('20.00'),
            total_usd=Decimal('20.00'),
            status='created'
        )
        self.currency = CryptoCurrency.objects.create(
            code='USDT', name='Tether', network='TRC20', precision=6
        )

    def test_create_invoice(self):
        expires_at = timezone.now() + timedelta(hours=1)
        invoice = CryptoPaymentService.create_invoice(
            booking_id=self.booking.id,
            currency_id=self.currency.id,
            amount_usd=Decimal('20.00'),
            amount_crypto=Decimal('20.00'),
            address='T1234567890',
            provider='nowpayments',
            provider_invoice_id='NP-123',
            expires_at=expires_at
        )
        self.assertEqual(invoice.status, 'pending')
        self.assertEqual(invoice.amount_usd, Decimal('20.00'))
        self.assertEqual(invoice.provider_invoice_id, 'NP-123')

    def test_paid_transition(self):
        invoice = CryptoPaymentService.create_invoice(
            booking_id=self.booking.id,
            currency_id=self.currency.id,
            amount_usd=Decimal('20.00'),
            amount_crypto=Decimal('20.00'),
            address='T1234567890',
            provider='nowpayments',
            provider_invoice_id='NP-123',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        CryptoPaymentService.mark_invoice_paid('NP-123')
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'paid')
        
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, 'paid')

class CryptoAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', username='test', password='password', role='client')
        self.vt = VehicleType.objects.create(code='scooter', name='Scooter')
        self.vm = VehicleModel.objects.create(
            name='NMAX', brand='Yamaha', type=self.vt, engine_cc=155,
            transmission='auto', fuel_consumption=2.5,
            year=2023, trunk='large', helmets_count=2, description='test', rental_terms='test'
        )
        self.vehicle = Vehicle.objects.create(
            model=self.vm, title='Yamaha NMAX', slug='nmax-1', sku='NMAX001',
            color='Black', base_price_usd=Decimal('20.00'), status='available'
        )
        self.booking = Booking.objects.create(
            public_number='BK-API',
            user=self.user,
            vehicle=self.vehicle,
            start_at=timezone.now() + timedelta(days=1),
            end_at=timezone.now() + timedelta(days=2),
            subtotal_usd=Decimal('20.00'),
            total_usd=Decimal('20.00'),
            status='created'
        )
        self.currency = CryptoCurrency.objects.create(
            code='USDT', name='Tether', network='TRC20', precision=6
        )
        self.create_url = reverse('crypto-invoice-create')
        self.webhook_url = reverse('crypto-webhook', kwargs={'provider': 'nowpayments'})

    def test_create_invoice_api(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "booking_id": self.booking.id,
            "currency_id": self.currency.id
        }
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('provider_invoice_id', response.data)

    def test_check_status_api(self):
        invoice = CryptoInvoice.objects.create(
            booking=self.booking, currency=self.currency, amount_usd=20, amount_crypto=20,
            address='addr1', provider='mock', provider_invoice_id='INV-1',
            expires_at=timezone.now() + timedelta(hours=1), status='pending'
        )
        self.client.force_authenticate(user=self.user)
        url = reverse('crypto-invoice-status', kwargs={'provider_invoice_id': 'INV-1'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'pending')

    def test_valid_webhook_success(self):
        invoice = CryptoInvoice.objects.create(
            booking=self.booking, currency=self.currency, amount_usd=20, amount_crypto=20,
            address='addr1', provider='nowpayments', provider_invoice_id='ORDER-123',
            expires_at=timezone.now() + timedelta(hours=1), status='pending'
        )
        payload = {
            "order_id": "ORDER-123",
            "status": "finished",
            "payment_id": "NP-999"
        }
        
        response = self.client.post(
            self.webhook_url, 
            data=payload, 
            format='json',
            HTTP_X_DEBUG_WEBHOOK='true',
            HTTP_X_EVENT_ID='EV-001'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'paid')
        self.assertTrue(WebhookProcessingLog.objects.filter(event_id='EV-001', status='success').exists())

    def test_invalid_signature_forbidden(self):
        # Without debug header and without valid signature it should fail
        response = self.client.post(
            self.webhook_url, 
            data={"status": "finished"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_webhook_idempotency(self):
        invoice = CryptoInvoice.objects.create(
            booking=self.booking, currency=self.currency, amount_usd=20, amount_crypto=20,
            address='addr1', provider='nowpayments', provider_invoice_id='ORDER-123',
            expires_at=timezone.now() + timedelta(hours=1), status='pending'
        )
        payload = {"order_id": "ORDER-123", "status": "finished"}
        
        # First time
        self.client.post(self.webhook_url, data=payload, format='json', HTTP_X_DEBUG_WEBHOOK='true', HTTP_X_EVENT_ID='DUP-1')
        # Second time
        response = self.client.post(self.webhook_url, data=payload, format='json', HTTP_X_DEBUG_WEBHOOK='true', HTTP_X_EVENT_ID='DUP-1')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(WebhookProcessingLog.objects.filter(event_id='DUP-1').count(), 1)
        self.assertEqual(WebhookProcessingLog.objects.filter(event_id='DUP-1', error_message="Already processed").count(), 1)
