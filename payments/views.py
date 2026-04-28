import json
from django.utils import timezone
from rest_framework import status, views, permissions, response
from django.shortcuts import get_object_or_404
from .models import Payment, PaymentWebhookEvent
from .serializers import PaymentCreateSerializer, PaymentResponseSerializer
from .providers import get_provider
from bookings.models import Booking
from bali_rent.permissions import IsBookingOwnerOrAdmin

class PaymentCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        booking = Booking.objects.get(id=serializer.validated_data['booking_id'])
        provider_name = serializer.validated_data['provider']
        
        provider = get_provider(provider_name)
        payment_data = provider.create_payment(booking, booking.total_usd)
        
        payment = Payment.objects.create(
            booking=booking,
            provider=provider_name,
            amount_usd=booking.total_usd,
            currency=booking.currency,
            status='pending',
            provider_payment_id=payment_data['provider_payment_id'],
            payment_url=payment_data['payment_url']
        )
        
        if booking.status == 'created':
            booking.status = 'pending_payment'
            booking.save()
            
        return response.Response(PaymentResponseSerializer(payment).data, status=status.HTTP_201_CREATED)

class PaymentDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsBookingOwnerOrAdmin]

    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        self.check_object_permissions(request, payment)
        return response.Response(PaymentResponseSerializer(payment).data)

class PaymentWebhookView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, provider_name='stripe'):
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

        # Unique event ID for idempotency
        event_id = payload.get('id') or payload.get('event_id')
        if not event_id:
            # Fallback for providers that don't send event ID
            import hashlib
            event_id = hashlib.md5(request.body).hexdigest()

        if PaymentWebhookEvent.objects.filter(provider=provider_name, event_id=event_id).exists():
            return response.Response({"status": "already processed"}, status=status.HTTP_200_OK)
        
        event_type = payload.get('type') or payload.get('event_type', 'unknown')
        
        webhook_event = PaymentWebhookEvent.objects.create(
            provider=provider_name,
            event_id=event_id,
            event_type=event_type,
            payload_json=payload
        )
        
        try:
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
                payment = Payment.objects.get(provider_payment_id=provider_payment_id)
                if payment.status != 'succeeded':
                    payment.status = 'succeeded'
                    payment.paid_at = timezone.now()
                    payment.save()
                    
                    booking = payment.booking
                    booking.payment_status = 'paid'
                    booking.status = 'confirmed'
                    booking.save()
            
            webhook_event.processed = True
            webhook_event.processed_at = timezone.now()
            webhook_event.save()
            
        except Payment.DoesNotExist:
            webhook_event.error_message = f"Payment {provider_payment_id} not found"
            webhook_event.save()
            return response.Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            webhook_event.error_message = str(e)
            webhook_event.save()
            return response.Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        return response.Response({"status": "success"}, status=status.HTTP_200_OK)
