from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import PromoCode, PromoCodeRedemption, Referral


class MarketingService:
    @staticmethod
    def _quantize(amount):
        return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def _get_validity_window(promo):
        starts_at = promo.starts_at or (promo.campaign.starts_at if promo.campaign_id else None)
        ends_at = promo.ends_at or (promo.campaign.ends_at if promo.campaign_id else None)
        return starts_at, ends_at

    @staticmethod
    def _get_usage_count(promo):
        # We'll use the current_usage field as source of truth for limits,
        # but also check the redemption count for integrity/test compatibility.
        return max(promo.current_usage, promo.redemptions.count())

    @staticmethod
    def calculate_discount(promo, amount):
        amount = Decimal(amount)
        discount = Decimal('0.00')

        if promo.discount_type == 'PERCENT':
            discount = (amount * promo.discount_value) / Decimal('100')
            if promo.max_discount_amount and discount > promo.max_discount_amount:
                discount = promo.max_discount_amount
        else:
            discount = promo.discount_value

        if discount > amount:
            discount = amount

        return MarketingService._quantize(discount)

    @staticmethod
    def validate_promo_code(code, user, amount, lock_for_update=False):
        try:
            if lock_for_update:
                promo = PromoCode.objects.select_for_update().select_related('campaign').get(code=code)
            else:
                promo = PromoCode.objects.select_related('campaign').get(code=code)
        except PromoCode.DoesNotExist:
            return None, 'Invalid promo code'

        if not promo.is_active:
            return None, 'Promo code is inactive'

        if promo.campaign_id and not promo.campaign.is_active:
            return None, 'Campaign is inactive'

        now = timezone.now()
        starts_at, ends_at = MarketingService._get_validity_window(promo)
        if starts_at and now < starts_at:
            return None, 'Promo code is not yet valid'
        if ends_at and now > ends_at:
            return None, 'Promo code expired'

        usage_count = MarketingService._get_usage_count(promo)
        if promo.usage_limit and usage_count >= promo.usage_limit:
            return None, 'Promo code usage limit reached'

        amount = Decimal(amount)
        if amount < promo.min_booking_amount:
            return None, f'Minimum booking amount for this code is {promo.min_booking_amount}'

        return promo, MarketingService.calculate_discount(promo, amount)

    @staticmethod
    @transaction.atomic
    def apply_promo_code(promo_or_code, user=None, booking=None, discount_amount=None, amount=None):
        """
        Atomically validate and increment promo code usage.
        """
        code = promo_or_code.code if isinstance(promo_or_code, PromoCode) else promo_or_code
        
        # We need a re-validation with lock
        # Use provided amount or booking.total or fallback
        val_amount = amount or (booking.total_usd if booking else Decimal('999999'))
        
        promo, result = MarketingService.validate_promo_code(
            code, user, val_amount, lock_for_update=True
        )
        
        if not promo:
            raise ValueError(result)

        if discount_amount is None and booking is not None:
            discount_amount = booking.discount_usd
        if discount_amount is None:
            discount_amount = Decimal('0.00')

        promo.current_usage = F('current_usage') + 1
        promo.save(update_fields=['current_usage'])
        promo.refresh_from_db(fields=['current_usage'])

        if booking is not None or user is not None or discount_amount:
            return PromoCodeRedemption.objects.create(
                promo_code=promo,
                user=user,
                booking=booking,
                discount_amount=MarketingService._quantize(Decimal(discount_amount)),
            )
        return None

    @staticmethod
    def create_referral(referrer, referred_user):
        return Referral.objects.create(referrer=referrer, referred_user=referred_user)
