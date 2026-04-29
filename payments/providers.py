import abc
import uuid
import hashlib
import hmac
import json
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from .models import Payment

class PaymentProvider(abc.ABC):
    @abc.abstractmethod
    def create_payment(self, booking, amount_usd):
        pass

    @abc.abstractmethod
    def verify_webhook(self, request):
        pass

class MockProvider(PaymentProvider):
    def create_payment(self, booking, amount_usd):
        payment_id = str(uuid.uuid4())
        return {
            'provider_payment_id': payment_id,
            'payment_url': f"https://mock-payment.com/{payment_id}",
            'status': 'pending'
        }

    def verify_webhook(self, request):
        return True

class StripeProvider(PaymentProvider):
    def __init__(self):
        try:
            import stripe
            stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
            self.stripe = stripe
        except ImportError:
            self.stripe = None

    def create_payment(self, booking, amount_usd):
        if not self.stripe or not self.stripe.api_key:
            return MockProvider().create_payment(booking, amount_usd)
        
        session = self.stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"Booking {booking.public_number}",
                    },
                    'unit_amount': int((Decimal(str(amount_usd)) * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=settings.PAYMENT_SUCCESS_URL,
            cancel_url=settings.PAYMENT_CANCEL_URL,
            client_reference_id=str(booking.id)
        )
        return {
            'provider_payment_id': session.id,
            'payment_url': session.url,
            'status': 'pending'
        }

    def verify_webhook(self, request):
        if not self.stripe:
            return False
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)

        try:
            event = self.stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
            return event
        except Exception:
            return False

class CryptoPaymentProvider(PaymentProvider):
    """
    Example implementation for a crypto provider like NowPayments or similar.
    Requires API_KEY and WEBHOOK_SECRET.
    """
    def __init__(self):
        self.api_key = getattr(settings, 'CRYPTO_PAYMENT_API_KEY', 'mock_key')
        self.webhook_secret = getattr(settings, 'CRYPTO_PAYMENT_WEBHOOK_SECRET', 'mock_secret')

    def create_payment(self, booking, amount_usd):
        # In a real implementation, this would call the crypto provider's API
        # to create an invoice/payment and return the URL.
        payment_id = f"crypto_{uuid.uuid4().hex[:12]}"
        return {
            'provider_payment_id': payment_id,
            'payment_url': f"https://crypto-gateway.com/pay/{payment_id}",
            'status': 'pending'
        }

    def verify_webhook(self, request):
        """
        Verify the crypto webhook signature.
        Assuming the provider sends a signature in a header.
        """
        signature = request.META.get('HTTP_X_NOWPAYMENTS_SIG')
        if not signature:
            return False
            
        # Standard HMAC-SHA512 verification example
        payload = request.body
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)

def get_provider(provider_name):
    if provider_name == 'stripe':
        return StripeProvider()
    if provider_name == 'crypto':
        return CryptoPaymentProvider()
    return MockProvider()
