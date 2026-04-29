from django.utils import timezone
from .models import PromoCode, Referral
from decimal import Decimal
from django.db import transaction

class MarketingService:
    @staticmethod
    def validate_promo_code(code, user, amount, lock_for_update=False):
        try:
            if lock_for_update:
                promo = PromoCode.objects.select_for_update().get(code=code)
            else:
                promo = PromoCode.objects.get(code=code)
        except PromoCode.DoesNotExist:
            return None, "Invalid promo code"

        if not promo.is_active:
            return None, "Promo code is inactive"
            
        now = timezone.now()
        if now < promo.valid_from:
            return None, "Promo code is not yet valid"
        if now > promo.valid_until:
            return None, "Promo code expired"
            
        if promo.current_usage >= promo.usage_limit:
            return None, "Promo code usage limit reached"
            
        if amount < promo.min_booking_amount:
            return None, f"Minimum booking amount for this code is {promo.min_booking_amount}"
            
        discount = Decimal('0.00')
        if promo.discount_type == 'PERCENT':
            discount = (amount * promo.value) / 100
            if promo.max_discount_amount and discount > promo.max_discount_amount:
                discount = promo.max_discount_amount
        else:
            discount = promo.value
            
        # Ensure discount is not greater than the amount itself
        if discount > amount:
            discount = amount
            
        return promo, discount

    @staticmethod
    @transaction.atomic
    def apply_promo_code(promo_or_code, user=None, amount=None):
        """
        Atomically validate and increment promo code usage.
        """
        code = promo_or_code.code if isinstance(promo_or_code, PromoCode) else promo_or_code
        
        # We need a re-validation with lock
        promo, result = MarketingService.validate_promo_code(
            code, user, amount or Decimal('999999'), lock_for_update=True
        )
        
        if not promo:
            raise ValueError(result)

        promo.current_usage += 1
        promo.save()
        return promo

    @staticmethod
    def create_referral(referrer, referred_user):
        return Referral.objects.create(referrer=referrer, referred_user=referred_user)
