from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db import transaction
from .models import (
    Season, ScooterSeasonPrice, OccupancyPricingRule, 
    DevicePricingRule, GeoPricingRule, PriceCalculationLog
)
from catalog.models import Vehicle
from addons.models import Addon
from delivery.models import DeliveryZone
from marketing.services import MarketingService
from bookings.models import Booking

class PricingCalculationService:
    @staticmethod
    def calculate_rental_days(start_at, end_at):
        duration = end_at - start_at
        days = duration.days
        if duration.seconds > 0:
            days += 1
        return max(days, 1)

    @staticmethod
    def get_seasonal_base_price(vehicle, start_at):
        # Look for a specific season price for this vehicle
        now_date = start_at.date()
        season_price = ScooterSeasonPrice.objects.filter(
            scooter=vehicle,
            season__start_date__lte=now_date,
            season__end_date__gte=now_date,
            season__is_active=True
        ).first()
        
        if season_price:
            return season_price.price_per_day, season_price.season.name
        
        return vehicle.base_price_usd, "Default"

    @staticmethod
    def calculate_occupancy_adjustment(vehicle, start_at, end_at, current_subtotal):
        # Occupancy is usually calculated as: rented_scooters / total_scooters
        # For simplicity, we'll implement a mock or basic calculation
        total_scooters = Vehicle.objects.filter(model=vehicle.model).count()
        if total_scooters == 0:
            return Decimal('0.00'), []

        rented_scooters = Booking.objects.filter(
            vehicle__model=vehicle.model,
            start_at__lt=end_at,
            end_at__gt=start_at
        ).exclude(status='cancelled').values('vehicle').distinct().count()
        
        occupancy_percent = (rented_scooters / total_scooters) * 100
        
        rules = OccupancyPricingRule.objects.filter(
            min_occupancy_percent__lte=occupancy_percent,
            max_occupancy_percent__gte=occupancy_percent,
            is_active=True
        )
        
        total_adjustment = Decimal('0.00')
        applied_rules = []
        for rule in rules:
            adjustment = (current_subtotal * rule.adjustment_percent) / 100
            total_adjustment += adjustment
            applied_rules.append({
                'name': rule.name,
                'occupancy': occupancy_percent,
                'adjustment_percent': float(rule.adjustment_percent),
                'value': float(adjustment)
            })
            
        return total_adjustment, applied_rules

    @staticmethod
    @transaction.atomic
    def calculate_full_price(vehicle_id, start_at, end_at, addon_ids=None, 
                            delivery_lat=None, delivery_lng=None, promo_code=None, 
                            device_platform=None, user_country=None, user=None, 
                            ip_address=None, user_agent=None):
        
        vehicle = Vehicle.objects.get(id=vehicle_id)
        rental_days = PricingCalculationService.calculate_rental_days(start_at, end_at)
        
        snapshot = {
            'input': {
                'vehicle_id': vehicle_id,
                'start_at': str(start_at),
                'end_at': str(end_at),
                'rental_days': rental_days,
                'addon_ids': addon_ids,
                'device_platform': device_platform,
                'user_country': user_country
            },
            'steps': []
        }

        # 1. Base Price & Season
        base_daily, season_name = PricingCalculationService.get_seasonal_base_price(vehicle, start_at)
        initial_subtotal = base_daily * rental_days
        
        current_subtotal = initial_subtotal
        snapshot['steps'].append({
            'step': 'base_price',
            'base_daily': float(base_daily),
            'season': season_name,
            'subtotal': float(initial_subtotal)
        })

        # 2. Occupancy Rule
        occ_adj, occ_rules = PricingCalculationService.calculate_occupancy_adjustment(vehicle, start_at, end_at, current_subtotal)
        current_subtotal += occ_adj
        snapshot['steps'].append({
            'step': 'occupancy_adjustment',
            'adjustment': float(occ_adj),
            'rules': occ_rules,
            'subtotal': float(current_subtotal)
        })

        # 3. Device Rule
        device_adj = Decimal('0.00')
        if device_platform:
            device_rule = DevicePricingRule.objects.filter(platform=device_platform, is_active=True).first()
            if device_rule:
                device_adj = (current_subtotal * device_rule.adjustment_percent) / 100
                current_subtotal += device_adj
                snapshot['steps'].append({
                    'step': 'device_adjustment',
                    'platform': device_platform,
                    'adjustment_percent': float(device_rule.adjustment_percent),
                    'adjustment': float(device_adj),
                    'subtotal': float(current_subtotal)
                })

        # 4. Geo Rule
        geo_adj = Decimal('0.00')
        if user_country:
            geo_rule = GeoPricingRule.objects.filter(country_code=user_country, is_active=True).first()
            if geo_rule:
                geo_adj = (current_subtotal * geo_rule.adjustment_percent) / 100
                current_subtotal += geo_adj
                snapshot['steps'].append({
                    'step': 'geo_adjustment',
                    'country': user_country,
                    'adjustment_percent': float(geo_rule.adjustment_percent),
                    'adjustment': float(geo_adj),
                    'subtotal': float(current_subtotal)
                })

        # 5. Addons
        addons_total = Decimal('0.00')
        addons_details = []
        if addon_ids:
            addons = Addon.objects.filter(id__in=addon_ids, is_active=True)
            for addon in addons:
                price = addon.price_usd
                if addon.price_type == 'per_day':
                    price *= rental_days
                addons_total += price
                addons_details.append({
                    'id': addon.id,
                    'name': addon.name,
                    'price': float(price)
                })
        
        snapshot['steps'].append({
            'step': 'addons',
            'details': addons_details,
            'total': float(addons_total)
        })

        # 6. Delivery
        delivery_price = Decimal('0.00')
        if delivery_lat and delivery_lng:
            # Simple zone check as before
            zones = DeliveryZone.objects.filter(is_active=True)
            for zone in zones:
                dist = ((zone.center_lat - float(delivery_lat))**2 + (zone.center_lng - float(delivery_lng))**2)**0.5 * 111
                if dist <= zone.radius_km:
                    if not zone.free_delivery:
                        delivery_price = zone.base_price_usd + (zone.price_per_km_usd * Decimal(str(dist)))
                    break
            else:
                delivery_price = Decimal('10.00') # Default fallback
        
        snapshot['steps'].append({
            'step': 'delivery',
            'price': float(delivery_price)
        })

        # 7. Discount / PromoCode
        discount_amount = Decimal('0.00')
        promo_details = None
        if promo_code:
            # Note: We pass the subtotal before delivery/addons for discount calculation 
            # or the whole sum? Usually it's on subtotal.
            promo, promo_discount = MarketingService.validate_promo_code(promo_code, user, current_subtotal)
            if promo:
                discount_amount = promo_discount
                promo_details = {
                    'code': promo_code,
                    'discount': float(discount_amount)
                }
        
        snapshot['steps'].append({
            'step': 'marketing',
            'promo': promo_details
        })

        # 8. Final Total
        final_total = current_subtotal + addons_total + delivery_price - discount_amount
        final_total = final_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        snapshot['final_total'] = float(final_total)

        # 9. Save Log
        log = PriceCalculationLog.objects.create(
            scooter=vehicle,
            user=user,
            calculation_snapshot=snapshot,
            total_price=final_total,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            'final_price': final_total,
            'currency': 'USD',
            'discount_amount': discount_amount,
            'delivery_price': delivery_price,
            'addons_total': addons_total,
            'price_calculation_id': log.id
        }
