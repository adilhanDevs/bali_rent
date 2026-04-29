from datetime import datetime, time
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from addons.models import Addon
from bookings.models import Booking
from catalog.models import Vehicle
from delivery.services import calculate_delivery_price
from marketing.services import MarketingService

from .models import (
    DevicePricingRule,
    GeoPricingRule,
    OccupancyPricingRule,
    PriceCalculationLog,
    ScooterSeasonPrice,
    Season,
)


TWOPLACES = Decimal('0.01')


class PricingCalculationService:
    DEFAULT_LOW_AVAILABILITY_PERCENT = 20
    DEFAULT_LOW_AVAILABILITY_SURCHARGE_PERCENT = Decimal('20.00')

    @staticmethod
    def calculate_rental_days(start_at, end_at):
        duration = end_at - start_at
        days = duration.days
        if duration.seconds > 0:
            days += 1
        return max(days, 1)

    @staticmethod
    def _to_aware_bounds(start_value, end_value):
        current_tz = timezone.get_current_timezone()

        if isinstance(start_value, datetime):
            start_at = timezone.make_aware(start_value, current_tz) if timezone.is_naive(start_value) else start_value
        else:
            start_at = timezone.make_aware(datetime.combine(start_value, time.min), current_tz)

        if isinstance(end_value, datetime):
            end_at = timezone.make_aware(end_value, current_tz) if timezone.is_naive(end_value) else end_value
        else:
            end_at = timezone.make_aware(datetime.combine(end_value, time.min), current_tz)

        return start_at, end_at

    @staticmethod
    def _quantize(value):
        return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    @staticmethod
    def _get_active_season(target_date):
        return (
            Season.objects.filter(
                is_active=True,
                start_date__lte=target_date,
                end_date__gte=target_date,
            )
            .order_by('start_date')
            .first()
        )

    @staticmethod
    def _get_seasonal_daily_price(vehicle, season):
        if not season:
            return vehicle.base_price_usd

        season_price = (
            ScooterSeasonPrice.objects.filter(scooter=vehicle, season=season)
            .order_by('-updated_at')
            .first()
        )
        if season_price:
            return season_price.price_per_day_usd
        return vehicle.base_price_usd

    @staticmethod
    def _calculate_occupancy(vehicle, start_at, end_at):
        total_scooters = Vehicle.objects.filter(model=vehicle.model).count()
        if total_scooters == 0:
            return 0, 100

        occupied_scooters = (
            Booking.objects.filter(
                vehicle__model=vehicle.model,
                start_at__lt=end_at,
                end_at__gt=start_at,
            )
            .exclude(status='cancelled')
            .values('vehicle')
            .distinct()
            .count()
        )
        occupancy_percent = int((occupied_scooters / total_scooters) * 100)
        availability_percent = max(0, 100 - occupancy_percent)
        return occupancy_percent, availability_percent

    @staticmethod
    def _get_occupancy_rule(occupancy_percent):
        return (
            OccupancyPricingRule.objects.filter(
                is_active=True,
                threshold_percent__lte=occupancy_percent,
            )
            .order_by('-threshold_percent')
            .first()
        )

    @staticmethod
    def _resolve_occupancy_increase_percent(occupancy_rule, availability_percent):
        configured_percent = occupancy_rule.price_increase_percent if occupancy_rule else None
        if availability_percent < PricingCalculationService.DEFAULT_LOW_AVAILABILITY_PERCENT:
            if configured_percent is None:
                return PricingCalculationService.DEFAULT_LOW_AVAILABILITY_SURCHARGE_PERCENT
            return max(configured_percent, PricingCalculationService.DEFAULT_LOW_AVAILABILITY_SURCHARGE_PERCENT)
        return configured_percent or Decimal('0.00')

    @staticmethod
    def _get_device_rule(device_type, country_code=None):
        if not device_type:
            return None

        queryset = DevicePricingRule.objects.filter(device_type=device_type, is_active=True)
        if country_code:
            exact_rule = queryset.filter(country_code=country_code).first()
            if exact_rule:
                return exact_rule
        return queryset.filter(Q(country_code__isnull=True) | Q(country_code='')).order_by('-updated_at').first()

    @staticmethod
    def _get_geo_rule(country_code=None, city=None):
        if not country_code:
            return None

        queryset = GeoPricingRule.objects.filter(country_code=country_code, is_active=True)
        if city:
            exact_city_rule = queryset.filter(city__iexact=city).first()
            if exact_city_rule:
                return exact_city_rule
        return queryset.filter(city='').order_by('-updated_at').first()

    @staticmethod
    def _calculate_multiplier_adjustment(amount, multiplier):
        return PricingCalculationService._quantize(amount * (multiplier - Decimal('1.00')))

    @staticmethod
    def _calculate_percentage_adjustment(amount, percent):
        return PricingCalculationService._quantize((amount * percent) / Decimal('100'))

    @staticmethod
    def _calculate_delivery_price(delivery_lat=None, delivery_lng=None):
        if delivery_lat is None or delivery_lng is None:
            return Decimal('0.00')
        delivery_result = calculate_delivery_price(delivery_lat, delivery_lng)
        return PricingCalculationService._quantize(delivery_result['price'])

    @staticmethod
    def _calculate_addons_total(addon_ids, rental_days):
        if not addon_ids:
            return Decimal('0.00'), []

        addons_total = Decimal('0.00')
        addon_details = []
        for addon in Addon.objects.filter(id__in=addon_ids, is_active=True):
            addon_price = addon.price_usd
            if addon.price_type == 'per_day':
                addon_price *= rental_days
            addon_price = PricingCalculationService._quantize(addon_price)
            addons_total += addon_price
            addon_details.append(
                {
                    'id': addon.id,
                    'name': addon.name,
                    'price': float(addon_price),
                }
            )
        return PricingCalculationService._quantize(addons_total), addon_details

    @staticmethod
    @transaction.atomic
    def calculate_full_price(
        vehicle_id,
        start_at,
        end_at,
        addon_ids=None,
        delivery_lat=None,
        delivery_lng=None,
        promo_code=None,
        device_platform=None,
        user_country=None,
        user=None,
        ip_address=None,
        user_agent=None,
        city=None,
    ):
        vehicle = Vehicle.objects.get(id=vehicle_id)
        start_at, end_at = PricingCalculationService._to_aware_bounds(start_at, end_at)
        rental_days = PricingCalculationService.calculate_rental_days(start_at, end_at)

        base_price = PricingCalculationService._quantize(vehicle.base_price_usd * rental_days)

        season = PricingCalculationService._get_active_season(start_at.date())
        seasonal_daily_price = PricingCalculationService._get_seasonal_daily_price(vehicle, season)
        season_multiplier = season.multiplier if season else Decimal('1.00')
        season_total = PricingCalculationService._quantize(seasonal_daily_price * rental_days * season_multiplier)
        season_adjustment = PricingCalculationService._quantize(season_total - base_price)

        running_total = season_total

        occupancy_percent, availability_percent = PricingCalculationService._calculate_occupancy(vehicle, start_at, end_at)
        occupancy_rule = PricingCalculationService._get_occupancy_rule(occupancy_percent)
        occupancy_adjustment = Decimal('0.00')
        occupancy_increase_percent = PricingCalculationService._resolve_occupancy_increase_percent(
            occupancy_rule,
            availability_percent,
        )
        if occupancy_increase_percent:
            occupancy_adjustment = PricingCalculationService._calculate_percentage_adjustment(
                running_total,
                occupancy_increase_percent,
            )
            running_total += occupancy_adjustment

        device_rule = PricingCalculationService._get_device_rule(device_platform, user_country)
        device_adjustment = Decimal('0.00')
        if device_rule:
            device_adjustment = PricingCalculationService._calculate_multiplier_adjustment(
                running_total,
                device_rule.multiplier,
            )
            running_total += device_adjustment

        geo_rule = PricingCalculationService._get_geo_rule(user_country, city)
        geo_adjustment = Decimal('0.00')
        if geo_rule:
            geo_adjustment = PricingCalculationService._calculate_multiplier_adjustment(
                running_total,
                geo_rule.multiplier,
            )
            running_total += geo_adjustment

        running_total = PricingCalculationService._quantize(running_total)

        addons_total, addon_details = PricingCalculationService._calculate_addons_total(addon_ids, rental_days)
        delivery_price = PricingCalculationService._calculate_delivery_price(delivery_lat, delivery_lng)

        discount_amount = Decimal('0.00')
        promo_details = None
        if promo_code:
            promo, promo_result = MarketingService.validate_promo_code(promo_code, user, running_total)
            if promo:
                discount_amount = PricingCalculationService._quantize(promo_result)
                promo_details = {'code': promo.code, 'discount_amount': float(discount_amount)}

        final_price = PricingCalculationService._quantize(running_total + addons_total + delivery_price - discount_amount)

        payload = {
            'input': {
                'scooter_id': vehicle.id,
                'start_date': start_at.date().isoformat(),
                'end_date': end_at.date().isoformat(),
                'rental_days': rental_days,
                'device_type': device_platform,
                'country_code': user_country,
                'city': city,
                'addon_ids': addon_ids or [],
                'promo_code': promo_code,
            },
            'breakdown': {
                'base_price': float(base_price),
                'season_adjustment': float(season_adjustment),
                'occupancy_adjustment': float(occupancy_adjustment),
                'device_adjustment': float(device_adjustment),
                'geo_adjustment': float(geo_adjustment),
                'addons_total': float(addons_total),
                'delivery_price': float(delivery_price),
                'discount_amount': float(discount_amount),
                'final_total': float(final_price),
            },
            'rules': {
                'season': season.code if season else None,
                'season_multiplier': float(season_multiplier),
                'occupancy_percent': occupancy_percent,
                'availability_percent': availability_percent,
                'occupancy_threshold': occupancy_rule.threshold_percent if occupancy_rule else None,
                'occupancy_increase_percent': float(occupancy_increase_percent),
                'occupancy_rule_source': (
                    'configured_rule'
                    if occupancy_rule
                    else 'default_low_availability'
                    if availability_percent < PricingCalculationService.DEFAULT_LOW_AVAILABILITY_PERCENT
                    else None
                ),
                'device_rule_id': device_rule.id if device_rule else None,
                'geo_rule_id': geo_rule.id if geo_rule else None,
            },
            'addons': addon_details,
            'promo': promo_details,
        }

        log = PriceCalculationLog.objects.create(
            scooter=vehicle,
            user=user,
            base_price=base_price,
            final_price=final_price,
            payload_json=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {
            'base_price': base_price,
            'season_adjustment': season_adjustment,
            'occupancy_adjustment': occupancy_adjustment,
            'device_adjustment': device_adjustment,
            'geo_adjustment': geo_adjustment,
            'final_total': final_price,
            'price_calculation_id': log.id,
            # Compatibility keys for existing booking flow.
            'final_price': final_price,
            'currency': 'USD',
            'discount_amount': discount_amount,
            'delivery_price': delivery_price,
            'addons_total': addons_total,
            'pricing_snapshot': payload,
        }
