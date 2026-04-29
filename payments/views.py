import json
from django.utils import timezone
from rest_framework import status, views, permissions, response
from django.shortcuts import get_object_or_404
from .models import Payment, PaymentWebhookEvent
from .serializers import PaymentCreateSerializer, PaymentResponseSerializer
from .providers import get_provider
from bookings.models import Booking
from bali_rent.permissions import IsBookingOwnerOrAdmin
from audit.mixins import AuditMixin

from rest_framework import throttling

class PaymentCreateView(AuditMixin, views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [throttling.ScopedRateThrottle]
    throttle_scope = 'payment_create'

    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        booking = Booking.objects.select_related('user').get(id=serializer.validated_data['booking_id'])
        provider_name = serializer.validated_data['provider']
        
        provider = get_provider(provider_name)
        payment_data = provider.create_payment(booking, booking.total_usd)
        
        payment = Payment.objects.create(
            booking=booking,
            provider=provider_name,
            method='crypto' if provider_name == 'crypto' else 'card',
            amount_usd=booking.total_usd,
            amount_display=f"{booking.currency} {booking.total_usd}",
            currency=booking.currency,
            status='pending',
            provider_payment_id=payment_data['provider_payment_id'],
            payment_url=payment_data['payment_url']
        )
        
        if booking.status == 'created':
            booking.status = 'pending_payment'
            booking.save()
            
        self._log_audit(payment, 'create', after_dict=PaymentResponseSerializer(payment).data)
        return response.Response(PaymentResponseSerializer(payment).data, status=status.HTTP_201_CREATED)

class PaymentDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsBookingOwnerOrAdmin]

    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        self.check_object_permissions(request, payment)
        return response.Response(PaymentResponseSerializer(payment).data)

from audit.services import AuditService, WebhookLogService

class PaymentWebhookView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, provider_name='stripe'):
        start_time = timezone.now()
        provider = get_provider(provider_name)
        
        # Verify signature
        if not provider.verify_webhook(request):
            return response.Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)
        
        payload = request.data
        if not isinstance(payload, dict):
            try:
                payload = json.loads(request.body)
            except:
                pass

        webhook_event = None
        from django.db import transaction
        try:
            with transaction.atomic():
                webhook_event, created = WebhookLogService.begin(provider_name, payload, request.body)

                if not created and webhook_event.processed:
                    return response.Response({"status": "already processed"}, status=status.HTTP_200_OK)
                
                event_type = webhook_event.event_type
                provider_payment_id = None
                success = False
                
                if provider_name == 'stripe':
                    if event_type == 'checkout.session.completed':
                        provider_payment_id = payload.get('data', {}).get('object', {}).get('id')
                        success = True
                elif provider_name == 'crypto':
                    # Example for NowPayments style
                    if payload.get('payment_status') == 'finished':
                        provider_payment_id = payload.get('payment_id')
                        success = True
                
                if provider_payment_id and success:
                    # Lock the payment record
                    try:
                        payment = Payment.objects.select_for_update().select_related('booking').get(provider_payment_id=provider_payment_id)
                        if payment.status != 'succeeded':
                            payment.status = 'succeeded'
                            payment.paid_at = timezone.now()
                            payment.save()
                            
                            booking = payment.booking
                            booking.payment_status = 'paid'
                            booking.status = 'confirmed'
                            booking.save()
                    except Payment.DoesNotExist:
                        WebhookLogService.mark_failure(webhook_event, f"Payment {provider_payment_id} not found", started_at=start_time)
                        return response.Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
                
                WebhookLogService.mark_success(webhook_event, started_at=start_time)
            
        except Exception as e:
            if webhook_event is not None:
                WebhookLogService.mark_failure(webhook_event, e, started_at=start_time)
            else:
                AuditService.log_webhook(
                    provider=provider_name,
                    event_id=WebhookLogService._event_id_from_payload(payload, request.body),
                    event_type=payload.get('type', 'unknown'),
                    payload=payload,
                    status='failure',
                    error_message=str(e),
                    processing_time_ms=int((timezone.now() - start_time).total_seconds() * 1000),
                )
            return response.Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        return response.Response({"status": "success"}, status=status.HTTP_200_OK)
