from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Booking, BookingAddon, AvailabilityBlock
from catalog.models import Vehicle
from addons.models import Addon
from delivery.models import DeliveryZone, DeliveryAddress
import uuid

class BookingPriceService:
    @staticmethod
    def calculate_rental_days(start_at, end_at):
        duration = end_at - start_at
        days = duration.days
        if duration.seconds > 0:
            days += 1
        return max(days, 1)

    @staticmethod
    def calculate_prices(vehicle, start_at, end_at, addon_ids=None, payment_method='online_card', delivery_lat=None, delivery_lng=None):
        rental_days = BookingPriceService.calculate_rental_days(start_at, end_at)
        
        # Base price
        base_price_per_day = vehicle.base_price_usd
        subtotal_usd = base_price_per_day * rental_days
        
        # Add-ons
        addons_total_usd = Decimal('0.00')
        addons_data = []
        if addon_ids:
            addons = Addon.objects.filter(id__in=addon_ids, is_active=True)
            for addon in addons:
                price = addon.price_usd
                if addon.price_type == 'per_day':
                    price *= rental_days
                addons_total_usd += price
                addons_data.append(addon)
        
        # Delivery price (simplified logic based on DeliveryZone)
        delivery_price_usd = Decimal('0.00')
        if delivery_lat and delivery_lng:
            # Simple logic: find first zone that contains coordinates (circular for now)
            # In a real app we might use PostGIS or more complex logic
            zones = DeliveryZone.objects.filter(is_active=True)
            for zone in zones:
                # Basic distance check (Euclidean distance is not accurate for lat/lng but okay for small distances)
                dist = ((zone.center_lat - delivery_lat)**2 + (zone.center_lng - delivery_lng)**2)**0.5 * 111 # rough km conversion
                if dist <= zone.radius_km:
                    if not zone.free_delivery:
                        delivery_price_usd = zone.base_price_usd + (zone.price_per_km_usd * Decimal(str(dist)))
                    break
            else:
                # If no zone found, maybe a default high price or error
                delivery_price_usd = Decimal('10.00') # Default

        # Discount/Markup
        discount_usd = Decimal('0.00')
        markup_usd = Decimal('0.00')
        
        if payment_method == 'cash_on_delivery':
            discount_usd = (subtotal_usd + addons_total_usd + delivery_price_usd) * Decimal('0.10')
        elif payment_method == 'card_on_delivery':
            markup_usd = (subtotal_usd + addons_total_usd + delivery_price_usd) * Decimal('0.10')
            
        total_usd = subtotal_usd + addons_total_usd + delivery_price_usd - discount_usd + markup_usd
        
        return {
            'rental_days': rental_days,
            'subtotal_usd': subtotal_usd,
            'addons_total_usd': addons_total_usd,
            'delivery_price_usd': delivery_price_usd,
            'discount_usd': discount_usd,
            'markup_usd': markup_usd,
            'total_usd': total_usd,
            'addons': addons_data
        }

class BookingAvailabilityService:
    @staticmethod
    def is_available(vehicle, start_at, end_at, exclude_booking_id=None):
        # Check AvailabilityBlock
        blocks = AvailabilityBlock.objects.filter(
            vehicle=vehicle,
            start_at__lt=end_at,
            end_at__gt=start_at
        )
        if exclude_booking_id:
            blocks = blocks.exclude(source_booking_id=exclude_booking_id)
            
        if blocks.exists():
            return False
            
        # Also check Bookings directly just in case (though blocks should cover it)
        bookings = Booking.objects.filter(
            vehicle=vehicle,
            start_at__lt=end_at,
            end_at__gt=start_at
        ).exclude(status='cancelled')
        
        if exclude_booking_id:
            bookings = bookings.exclude(id=exclude_booking_id)
            
        if bookings.exists():
            return False
            
        return True

class BookingCreationService:
    @staticmethod
    @transaction.atomic
    def create_booking(user, vehicle_id, start_at, end_at, addon_ids=None, payment_method='online_card', 
                       delivery_address_text=None, delivery_lat=None, delivery_lng=None, currency='USD'):
        
        vehicle = Vehicle.objects.select_for_update().get(id=vehicle_id)
        
        if not BookingAvailabilityService.is_available(vehicle, start_at, end_at):
            raise ValueError("Vehicle is not available for selected dates.")
            
        price_details = BookingPriceService.calculate_prices(
            vehicle, start_at, end_at, addon_ids, payment_method, delivery_lat, delivery_lng
        )
        
        # Create delivery address if provided
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
            delivery_price_usd=price_details['delivery_price_usd'],
            payment_method=payment_method,
            currency=currency,
            subtotal_usd=price_details['subtotal_usd'],
            addons_total_usd=price_details['addons_total_usd'],
            discount_usd=price_details['discount_usd'],
            markup_usd=price_details['markup_usd'],
            total_usd=price_details['total_usd'],
            total_display=f"{currency} {price_details['total_usd']}", # Simplified
            status='created'
        )
        
        # Create booking addons
        for addon in price_details['addons']:
            BookingAddon.objects.create(
                booking=booking,
                addon=addon,
                name_snapshot=addon.name,
                price_usd_snapshot=addon.price_usd,
                quantity=1
            )
            
        # Create availability block
        AvailabilityBlock.objects.create(
            vehicle=vehicle,
            start_at=start_at,
            end_at=end_at,
            type='booking',
            source_booking=booking
        )
        
        return booking
