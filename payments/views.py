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
        
        # Update booking status to pending_payment if it was created
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

    def post(self, request):
        # Determine provider from path or headers, assume stripe for now
        provider_name = 'stripe'
        provider = get_provider(provider_name)
        
        # In a real scenario, we'd verify the signature
        # event = provider.verify_webhook(request)
        # if not event:
        #     return response.Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)
        
        payload = request.data
        # Simulating stripe event structure for mock/dev
        event_id = payload.get('id', 'mock_event_' + str(timezone.now().timestamp()))
        event_type = payload.get('type', 'checkout.session.completed')
        
        # Idempotency check
        if PaymentWebhookEvent.objects.filter(provider=provider_name, event_id=event_id).exists():
            return response.Response({"status": "already processed"}, status=status.HTTP_200_OK)
        
        webhook_event = PaymentWebhookEvent.objects.create(
            provider=provider_name,
            event_id=event_id,
            event_type=event_type,
            payload_json=payload
        )
        
        try:
            if event_type == 'checkout.session.completed':
                # For Stripe, the client_reference_id or provider_payment_id would be used
                session = payload.get('data', {}).get('object', {})
                provider_payment_id = session.get('id')
                
                payment = Payment.objects.get(provider_payment_id=provider_payment_id)
                if payment.status != 'succeeded':
                    payment.status = 'succeeded'
                    payment.paid_at = timezone.now()
                    payment.save()
                    
                    booking = payment.booking
                    booking.payment_status = 'paid'
                    booking.status = 'confirmed' # confirmed after payment
                    booking.save()
                    
            webhook_event.processed = True
            webhook_event.processed_at = timezone.now()
            webhook_event.save()
            
        except Payment.DoesNotExist:
            webhook_event.error_message = "Payment not found"
            webhook_event.save()
            return response.Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            webhook_event.error_message = str(e)
            webhook_event.save()
            return response.Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        return response.Response({"status": "success"}, status=status.HTTP_200_OK)
