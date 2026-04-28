import hmac
import hashlib
import json
import time
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import views, response, status, permissions
from .serializers import (
    CryptoInvoiceCreateSerializer, CryptoInvoiceResponseSerializer,
    CryptoInvoiceStatusSerializer
)
from .models import CryptoInvoice, CryptoCurrency
from .services import CryptoPaymentService
from audit.models import WebhookProcessingLog
from bookings.models import Booking
from bali_rent.permissions import IsBookingOwnerOrAdmin

class CryptoInvoiceCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CryptoInvoiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        booking = get_object_or_404(Booking, id=serializer.validated_data['booking_id'], user=request.user)
        currency = get_object_or_404(CryptoCurrency, id=serializer.validated_data['currency_id'], is_active=True)
        
        # In a real app, here we would call the external provider API (e.g., NowPayments)
        # to get a real address and invoice ID.
        # For this implementation, we simulate it.
        import uuid
        provider_invoice_id = f"CRYP-{uuid.uuid4().hex[:10].upper()}"
        
        # Assume 1:1 rate for mock or fetch real rate
        amount_crypto = booking.total_usd 
        
        invoice = CryptoPaymentService.create_invoice(
            booking_id=booking.id,
            currency_id=currency.id,
            amount_usd=booking.total_usd,
            amount_crypto=amount_crypto,
            address="MOCK_CRYPTO_ADDRESS_" + uuid.uuid4().hex[:8],
            provider="mock_provider",
            provider_invoice_id=provider_invoice_id,
            expires_at=timezone.now() + timezone.timedelta(hours=1),
            payment_url=f"https://mock-crypto.com/pay/{provider_invoice_id}"
        )
        
        return response.Response(CryptoInvoiceResponseSerializer(invoice).data, status=status.HTTP_201_CREATED)

class CryptoInvoiceStatusView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsBookingOwnerOrAdmin]

    def get(self, request, provider_invoice_id):
        invoice = get_object_or_404(CryptoInvoice, provider_invoice_id=provider_invoice_id)
        self.check_object_permissions(request, invoice.booking)
        return response.Response(CryptoInvoiceStatusSerializer(invoice).data)

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class CryptoWebhookView(views.APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = [] # Disable CSRF and Session checks for webhooks

    def post(self, request, provider='nowpayments'):
        start_time = time.time()
        
        # 1. Verify Signature
        if not self._verify_signature(request, provider):
            return response.Response({"error": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)
        
        payload = request.data
        # Use a default if event ID is missing
        external_event_id = request.META.get('HTTP_X_EVENT_ID') or f"evt_{int(time.time()*1000)}"
        event_type = payload.get('event_type') or payload.get('status', 'unknown')
        
        # 2. Logging & Idempotency
        log = WebhookProcessingLog.objects.create(
            provider=provider,
            event_id=external_event_id,
            event_type=event_type,
            status='pending'
        )
        
        try:
            event, processed = CryptoPaymentService.process_webhook_event(
                provider=provider,
                external_event_id=external_event_id,
                event_type=event_type,
                payload=payload
            )
            
            log.status = 'success'
            if not processed:
                log.error_message = "Already processed"
            
        except Exception as e:
            log.status = 'failure'
            log.error_message = str(e)
            
        log.processing_time_ms = int((time.time() - start_time) * 1000)
        log.save()
        
        if log.status == 'failure':
            return response.Response({"error": log.error_message}, status=status.HTTP_400_BAD_REQUEST)
            
        return response.Response({"status": "ok"})

    def _verify_signature(self, request, provider):
        # Simulation of signature verification
        # In a real app, use settings.CRYPTO_WEBHOOK_SECRET
        secret = "mock_secret" 
        signature = request.META.get('HTTP_X_NOWPAYMENTS_SIG')
        
        debug_header = request.META.get('HTTP_X_DEBUG_WEBHOOK')
        
        if not signature:
            # For testing/dev purposes
            import sys
            is_testing = 'test' in sys.argv
            if (settings.DEBUG or is_testing) and str(debug_header).lower() == 'true':
                return True
            return False
            
        expected_sig = hmac.new(
            secret.encode(),
            request.body,
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_sig)
            
        expected_sig = hmac.new(
            secret.encode(),
            request.body,
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_sig)
