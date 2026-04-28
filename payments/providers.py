import abc
import uuid
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
        # In mock, we trust the payload if a specific header is present or just return true
        return True

class StripeProvider(PaymentProvider):
    def __init__(self):
        # Import stripe here to avoid hard dependency if not used
        try:
            import stripe
            stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
            self.stripe = stripe
        except ImportError:
            self.stripe = None

    def create_payment(self, booking, amount_usd):
        if not self.stripe or not self.stripe.api_key:
            # Fallback to mock if not configured
            return MockProvider().create_payment(booking, amount_usd)
        
        # Real Stripe implementation would go here
        # For Phase 1, we can keep it simple or use mock-like behavior if not fully set up
        session = self.stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"Booking {booking.public_number}",
                    },
                    'unit_amount': int(amount_usd * 100),
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

def get_provider(provider_name):
    if provider_name == 'stripe':
        return StripeProvider()
    return MockProvider()
