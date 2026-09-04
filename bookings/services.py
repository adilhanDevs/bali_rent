from decimal import Decimal, ROUND_HALF_UP
from copy import deepcopy
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from .models import Booking, BookingAddon, AvailabilityBlock
from catalog.models import Vehicle
from addons.models import Addon
from delivery.models import DeliveryAddress
from pricing.services import PricingCalculationService
from pricing.models import PriceCalculationLog
from marketing.services import MarketingService
from marketing.models import PromoCode
from payments.services import PaymentAdjustmentService
from audit.services import AuditService
from analytics.services import AnalyticsService
from notifications.services import NotificationService
from chat.models import ChatMessage, ChatParticipant, ChatThread
from users.models import User
import uuid

class BookingPriceService:
    @staticmethod
    def calculate_rental_days(start_at, end_at):
        return PricingCalculationService.calculate_rental_days(start_at, end_at)

    @staticmethod
    def calculate_prices(vehicle, start_at, end_at, addon_ids=None, payment_method='online_card', 
                         delivery_lat=None, delivery_lng=None, promo_code=None, user=None, 
                         device_platform=None, user_country=None):
        
        # Delegate to the new pricing service
        pricing_result = PricingCalculationService.calculate_full_price(
            vehicle_id=vehicle.id,
            start_at=start_at,
            end_at=end_at,
            addon_ids=addon_ids,
            delivery_lat=delivery_lat,
            delivery_lng=delivery_lng,
            promo_code=promo_code,
            device_platform=device_platform,
            user_country=user_country,
            user=user
        )
        
        final_price = pricing_result['final_price']
        discount_usd = pricing_result['discount_amount']
        payment_adjustment = PaymentAdjustmentService.apply_adjustment(final_price, payment_method)
        final_price = payment_adjustment['adjusted_total_usd']
        discount_usd += payment_adjustment['discount_usd']
        markup_usd = payment_adjustment['markup_usd']

        # Mirror the same percentage payment-method adjustment on the exact IDR total computed
        # in pricing_result, instead of converting the USD total through a currency rate.
        adjustment_percent = payment_adjustment['adjustment_percent']
        final_total_idr = pricing_result['final_total_idr']
        adjustment_amount_idr = int(
            (Decimal(final_total_idr) * adjustment_percent / Decimal('100')).to_integral_value(rounding=ROUND_HALF_UP)
        )
        final_total_idr += adjustment_amount_idr
        discount_idr = pricing_result['discount_amount_idr'] + (abs(adjustment_amount_idr) if adjustment_amount_idr < 0 else 0)
        markup_idr = adjustment_amount_idr if adjustment_amount_idr > 0 else 0

        return {
            'rental_days': PricingCalculationService.calculate_rental_days(start_at, end_at),
            'subtotal_usd': final_price - pricing_result['addons_total'] - pricing_result['delivery_price'] + discount_usd - markup_usd,
            'addons_total_usd': pricing_result['addons_total'],
            'delivery_price_usd': pricing_result['delivery_price'],
            'discount_usd': discount_usd,
            'markup_usd': markup_usd,
            'total_usd': final_price,
            'subtotal_idr': pricing_result['running_total_idr'],
            'addons_total_idr': pricing_result['addons_total_idr'],
            'delivery_price_idr': pricing_result['delivery_price_idr'],
            'discount_idr': discount_idr,
            'markup_idr': markup_idr,
            'total_idr': final_total_idr,
            'price_calculation_id': pricing_result['price_calculation_id'],
            'applied_tariff': pricing_result.get('applied_tariff'),
        }

class BookingAvailabilityService:
    @staticmethod
    def _normalize_bound(value):
        if not isinstance(value, str):
            return value
        parsed = parse_datetime(value)
        if parsed is None:
            parsed_date = parse_date(value)
            if parsed_date is None:
                raise ValueError('Invalid availability date/time.')
            parsed = timezone.datetime.combine(parsed_date, timezone.datetime.min.time())
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed

    @staticmethod
    def is_available(vehicle, start_at, end_at, exclude_booking_id=None):
        # A card can stand in for several identical physical units (vehicle.quantity). It stays
        # bookable until every unit is taken for the requested window, so we count how many units
        # are already occupied instead of failing on the first overlap.
        return BookingAvailabilityService.units_available(
            vehicle, start_at, end_at, exclude_booking_id=exclude_booking_id
        ) > 0

    @staticmethod
    def units_available(vehicle, start_at, end_at, exclude_booking_id=None):
        start_at = BookingAvailabilityService._normalize_bound(start_at)
        end_at = BookingAvailabilityService._normalize_bound(end_at)

        blocks = AvailabilityBlock.objects.filter(
            vehicle=vehicle,
            start_at__lt=end_at,
            end_at__gt=start_at
        )
        if exclude_booking_id:
            blocks = blocks.exclude(source_booking_id=exclude_booking_id)

        from catalog.models import VehicleMaintenance
        maintenance = VehicleMaintenance.objects.filter(
            vehicle=vehicle,
            start_at__lt=end_at,
            end_at__gt=start_at,
            status__in=['scheduled', 'in_progress']
        )

        intervals = list(blocks.values_list('start_at', 'end_at')) + list(
            maintenance.values_list('start_at', 'end_at')
        )
        events = []
        for occupied_start, occupied_end in intervals:
            clipped_start = max(start_at, occupied_start)
            clipped_end = min(end_at, occupied_end)
            if clipped_start >= clipped_end:
                continue
            events.append((clipped_start, 1))
            events.append((clipped_end, -1))

        # End before start at identical timestamps keeps back-to-back reservations independent.
        events.sort(key=lambda item: (item[0], item[1]))
        occupied = 0
        peak_occupied = 0
        for _, delta in events:
            occupied += delta
            peak_occupied = max(peak_occupied, occupied)
        return max((vehicle.quantity or 1) - peak_occupied, 0)

class BookingCreationService:
    @staticmethod
    def _initial_booking_status(payment_method):
        if payment_method in {'cash_on_delivery', 'card_on_delivery'}:
            return 'confirmed'
        return 'created'

    @staticmethod
    def _create_support_thread(booking):
        thread = ChatThread.objects.create(
            title=f"Booking {booking.public_number}",
            created_by=booking.user,
        )
        ChatParticipant.objects.create(thread=thread, user=booking.user, role=ChatParticipant.ROLE_CLIENT)

        staff_user = User.objects.filter(role__in=['manager', 'admin', 'staff'], is_active=True).order_by('id').first()
        if staff_user:
            role = ChatParticipant.ROLE_MANAGER if staff_user.role == 'manager' else ChatParticipant.ROLE_STAFF
            ChatParticipant.objects.get_or_create(thread=thread, user=staff_user, defaults={'role': role})

        start_str = booking.start_at.strftime('%d %b %Y, %H:%M') if hasattr(booking.start_at, 'strftime') else str(booking.start_at)
        end_str = booking.end_at.strftime('%d %b %Y, %H:%M') if hasattr(booking.end_at, 'strftime') else str(booking.end_at)
        rental_days = BookingPriceService.calculate_rental_days(booking.start_at, booking.end_at)
        delivery_info = booking.delivery_address.address_text if booking.delivery_address else 'Self pickup'

        msg_text = (
            f"🛵 Booking #{booking.public_number}\n"
            f"Scooter: {booking.vehicle.title}\n"
            f"Rental: {start_str} → {end_str} ({rental_days} days)\n"
            f"Total: ${booking.total_usd} ({booking.payment_method})\n"
            f"Delivery: {delivery_info}"
        )

        ChatMessage.objects.create(
            thread=thread,
            sender=booking.user,
            text=msg_text,
        )
        return thread

    @staticmethod
    @transaction.atomic
    def create_booking(user, vehicle_id, start_at, end_at, addon_ids=None, payment_method='online_card',
                       delivery_time=None, delivery_address_text=None, delivery_lat=None, delivery_lng=None,
                       currency='USD', promo_code=None, request_info=None, contact_name=None, contact_phone=None,
                       contact_has_telegram=False, contact_has_wechat=False, contact_has_whatsapp=False):
        
        vehicle = Vehicle.objects.select_for_update().get(id=vehicle_id)
        
        if not BookingAvailabilityService.is_available(vehicle, start_at, end_at):
            raise ValueError("Vehicle is not available for selected dates.")
            
        request_info = request_info or {}
        device_platform = request_info.get('platform')
        user_country = request_info.get('country')
        ip = request_info.get('ip')
        ua = request_info.get('user_agent')

        pricing_result = PricingCalculationService.calculate_full_price(
            vehicle_id=vehicle.id,
            start_at=start_at,
            end_at=end_at,
            addon_ids=addon_ids,
            delivery_lat=delivery_lat,
            delivery_lng=delivery_lng,
            promo_code=promo_code,
            device_platform=device_platform,
            user_country=user_country,
            user=user,
            ip_address=ip,
            user_agent=ua
        )
        
        total_usd = pricing_result['final_price']
        discount_usd = pricing_result['discount_amount']
        payment_adjustment = PaymentAdjustmentService.apply_adjustment(total_usd, payment_method)
        total_usd = payment_adjustment['adjusted_total_usd']
        discount_usd += payment_adjustment['discount_usd']
        markup_usd = payment_adjustment['markup_usd']
        subtotal_usd = total_usd - pricing_result['addons_total'] - pricing_result['delivery_price'] + discount_usd - markup_usd

        pricing_snapshot = deepcopy(pricing_result.get('pricing_snapshot') or {})
        pricing_snapshot['payment_adjustment'] = {
            'payment_method': payment_method,
            'adjustment_percent': str(payment_adjustment['adjustment_percent']),
            'adjustment_amount': str(payment_adjustment['adjustment_amount']),
            'discount_usd': str(payment_adjustment['discount_usd']),
            'markup_usd': str(payment_adjustment['markup_usd']),
            'adjusted_total_usd': str(payment_adjustment['adjusted_total_usd']),
        }
        pricing_snapshot['booking_totals'] = {
            'subtotal_usd': str(subtotal_usd),
            'addons_total_usd': str(pricing_result['addons_total']),
            'delivery_price_usd': str(pricing_result['delivery_price']),
            'discount_usd': str(discount_usd),
            'markup_usd': str(markup_usd),
            'total_usd': str(total_usd),
            'currency': currency,
        }

        delivery_address = None
        if delivery_address_text:
            delivery_address = DeliveryAddress.objects.create(
                user=user,
                address_text=delivery_address_text,
                lat=delivery_lat or 0,
                lng=delivery_lng or 0
            )
            
        public_number = f"BK-{uuid.uuid4().hex[:8].upper()}"
        resolved_contact_name = (contact_name or user.full_name or '').strip()
        resolved_contact_phone = (contact_phone or user.phone or '').strip()
        
        initial_status = BookingCreationService._initial_booking_status(payment_method)
        effective_delivery_time = delivery_time or start_at

        booking = Booking.objects.create(
            public_number=public_number,
            user=user,
            vehicle=vehicle,
            start_at=start_at,
            end_at=end_at,
            delivery_address=delivery_address,
            delivery_time=effective_delivery_time,
            delivery_price_usd=pricing_result['delivery_price'],
            payment_method=payment_method,
            currency=currency,
            subtotal_usd=subtotal_usd,
            addons_total_usd=pricing_result['addons_total'],
            discount_usd=discount_usd,
            markup_usd=markup_usd,
            total_usd=total_usd,
            total_display=f"{currency} {total_usd}",
            pricing_snapshot_json=pricing_snapshot,
            contact_name=resolved_contact_name,
            contact_phone=resolved_contact_phone,
            contact_has_telegram=bool(contact_has_telegram),
            contact_has_wechat=bool(contact_has_wechat),
            contact_has_whatsapp=bool(contact_has_whatsapp),
            status=initial_status
        )
        
        if pricing_result.get('price_calculation_id'):
            PriceCalculationLog.objects.filter(id=pricing_result['price_calculation_id']).update(booking=booking)

        if promo_code:
            try:
                MarketingService.apply_promo_code(
                    promo_code, 
                    user=user, 
                    booking=booking, 
                    discount_amount=discount_usd,
                    amount=total_usd
                )
            except ValueError as e:
                # If it was valid during calculate but invalid now (race condition)
                raise ValueError(f"Promo code error: {str(e)}")
        
        if addon_ids:
            addons = Addon.objects.filter(id__in=addon_ids)
            for addon in addons:
                BookingAddon.objects.create(
                    booking=booking,
                    addon=addon,
                    name_snapshot=addon.name,
                    price_usd_snapshot=addon.price_usd,
                    quantity=1
                )
            
        AvailabilityBlock.objects.create(
            vehicle=vehicle,
            start_at=start_at,
            end_at=end_at,
            type='booking',
            source_booking=booking
        )

        BookingCreationService._create_support_thread(booking)
        
        # Audit log
        from .serializers import BookingSerializer
        AuditService.log_mutation(
            user=user,
            obj=booking,
            action='create',
            after_dict=BookingSerializer(booking).data,
            ip_address=ip,
            user_agent=ua
        )
        
        AnalyticsService.track_event(
            user=user,
            event_name='booking_created',
            properties={
                'booking_id': booking.id,
                'total_usd': str(booking.total_usd),
                'vehicle_sku': vehicle.sku,
            },
            ip_address=ip,
            user_agent=ua
        )

        if payment_method == 'online_card':
            NotificationService.create_notification(
                user,
                f'Booking {booking.public_number} created',
                'Your booking was created. Complete payment to confirm it.',
                'booking_created',
                {'booking_id': booking.id, 'status': booking.status},
            )
        else:
            NotificationService.create_notification(
                user,
                f'Booking {booking.public_number} confirmed',
                'Your booking has been confirmed and is awaiting delivery.',
                'booking_confirmed',
                {'booking_id': booking.id, 'status': booking.status},
            )
        
        return booking
