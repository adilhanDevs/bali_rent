from django.db import transaction
from django.utils import timezone
from .models import CryptoCurrency, CryptoInvoice
from bookings.models import Booking

class CryptoPaymentService:
    @staticmethod
    def create_invoice(booking_id, currency_id, amount_usd, amount_crypto, address, provider, provider_invoice_id, expires_at, payment_url=''):
        booking = Booking.objects.get(id=booking_id)
        currency = CryptoCurrency.objects.get(id=currency_id)
        
        return CryptoInvoice.objects.create(
            booking=booking,
            currency=currency,
            amount_usd=amount_usd,
            amount_crypto=amount_crypto,
            address=address,
            provider=provider,
            provider_invoice_id=provider_invoice_id,
            expires_at=expires_at,
            payment_url=payment_url,
            status='pending'
        )

    @staticmethod
    def get_invoice_status(provider_invoice_id):
        invoice = CryptoInvoice.objects.get(provider_invoice_id=provider_invoice_id)
        return invoice.status

    @staticmethod
    @transaction.atomic
    def mark_invoice_paid(provider_invoice_id):
        invoice = CryptoInvoice.objects.select_for_update().get(provider_invoice_id=provider_invoice_id)
        
        if invoice.status == 'paid':
            return invoice

        if invoice.status in ['failed', 'expired']:
            # Depending on business rules, we might allow late payments or not.
            # For now, let's allow it if the provider says it's paid.
            pass

        invoice.status = 'paid'
        invoice.save()
        
        # Update booking
        booking = invoice.booking
        booking.payment_status = 'paid'
        # If the booking was pending payment, move it to confirmed
        if booking.status in ['created', 'pending_payment']:
            booking.status = 'confirmed'
        booking.save()
        
        return invoice

    @staticmethod
    @transaction.atomic
    def mark_invoice_failed(provider_invoice_id):
        invoice = CryptoInvoice.objects.select_for_update().get(provider_invoice_id=provider_invoice_id)
        
        if invoice.status == 'paid':
            # Cannot fail a paid invoice
            raise ValueError("Cannot mark a paid invoice as failed")
            
        invoice.status = 'failed'
        invoice.save()
        
        # Update booking if needed
        # booking = invoice.booking
        # booking.payment_status = 'failed'
        # booking.save()
        
        return invoice

    @staticmethod
    @transaction.atomic
    def process_webhook_event(provider, external_event_id, event_type, payload):
        from audit.services import WebhookLogService

        event, created = WebhookLogService.begin(
            provider,
            {'external_event_id': external_event_id, 'event_type': event_type, **(payload or {})},
            event_type=event_type,
        )
        
        if not created and event.processed:
            if event.error_message != "Already processed":
                event.error_message = "Already processed"
                event.save(update_fields=['error_message'])
            return event, False # Already processed

        # If not created but not processed, we update details if needed (unlikely for webhooks)
        
        # Process logic based on event_type
        # Example for generic payment success
        if event_type == 'payment_success' or payload.get('status') == 'finished':
            provider_invoice_id = payload.get('order_id') or payload.get('payment_id')
            if provider_invoice_id:
                try:
                    CryptoPaymentService.mark_invoice_paid(provider_invoice_id)
                except CryptoInvoice.DoesNotExist:
                    # Log or handle missing invoice
                    pass
        
        elif event_type == 'payment_failed' or payload.get('status') == 'failed':
            provider_invoice_id = payload.get('order_id') or payload.get('payment_id')
            if provider_invoice_id:
                try:
                    CryptoPaymentService.mark_invoice_failed(provider_invoice_id)
                except CryptoInvoice.DoesNotExist:
                    pass
                except ValueError:
                    # e.g. already paid
                    pass

        event.processed = True
        event.processed_at = timezone.now()
        event.status = 'success'
        event.save(update_fields=['processed', 'processed_at', 'status'])
        
        return event, True
