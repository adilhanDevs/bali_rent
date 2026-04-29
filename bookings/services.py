from decimal import Decimal
from copy import deepcopy
from django.db import transaction
from django.utils import timezone
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
            
        return {
            'rental_days': PricingCalculationService.calculate_rental_days(start_at, end_at),
            'subtotal_usd': final_price - pricing_result['addons_total'] - pricing_result['delivery_price'] + discount_usd - markup_usd,
            'addons_total_usd': pricing_result['addons_total'],
            'delivery_price_usd': pricing_result['delivery_price'],
            'discount_usd': discount_usd,
            'markup_usd': markup_usd,
            'total_usd': final_price,
            'price_calculation_id': pricing_result['price_calculation_id']
        }

class BookingAvailabilityService:
    @staticmethod
    def is_available(vehicle, start_at, end_at, exclude_booking_id=None):
        blocks = AvailabilityBlock.objects.filter(
            vehicle=vehicle,
            start_at__lt=end_at,
            end_at__gt=start_at
        )
        if exclude_booking_id:
            blocks = blocks.exclude(source_booking_id=exclude_booking_id)
        return not blocks.exists()

class BookingCreationService:
    @staticmethod
    @transaction.atomic
    def create_booking(user, vehicle_id, start_at, end_at, addon_ids=None, payment_method='online_card', 
                       delivery_address_text=None, delivery_lat=None, delivery_lng=None, 
                       currency='USD', promo_code=None, request_info=None):
        
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
            'adjustment_percent': float(payment_adjustment['adjustment_percent']),
            'adjustment_amount': float(payment_adjustment['adjustment_amount']),
            'discount_usd': float(payment_adjustment['discount_usd']),
            'markup_usd': float(payment_adjustment['markup_usd']),
            'adjusted_total_usd': float(payment_adjustment['adjusted_total_usd']),
        }
        pricing_snapshot['booking_totals'] = {
            'subtotal_usd': float(subtotal_usd),
            'addons_total_usd': float(pricing_result['addons_total']),
            'delivery_price_usd': float(pricing_result['delivery_price']),
            'discount_usd': float(discount_usd),
            'markup_usd': float(markup_usd),
            'total_usd': float(total_usd),
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
        
        booking = Booking.objects.create(
            public_number=public_number,
            user=user,
            vehicle=vehicle,
            start_at=start_at,
            end_at=end_at,
            delivery_address=delivery_address,
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
            status='created'
        )
        
        PriceCalculationLog.objects.filter(id=pricing_result['price_calculation_id']).update(booking=booking)

        if promo_code:
            promo = PromoCode.objects.filter(code=promo_code).first()
            if promo and discount_usd > Decimal('0.00'):
                MarketingService.apply_promo_code(
                    promo,
                    user=user,
                    booking=booking,
                    discount_amount=discount_usd,
                )
        
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
        
        AuditService.log_action(
            user=user,
            obj=booking,
            action='create',
            changes={'total_usd': str(booking.total_usd), 'vehicle': vehicle.sku},
            ip_address=ip,
            user_agent=ua
        )
        
        AnalyticsService.track_event(
            user=user,
            event_name='booking_created',
            properties={
                'booking_id': booking.id,
                'total_usd': float(booking.total_usd),
                'vehicle_sku': vehicle.sku,
            },
            ip_address=ip,
            user_agent=ua
        )
        
        return booking
