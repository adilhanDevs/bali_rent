from decimal import Decimal, ROUND_HALF_UP

from .models import PaymentMethodAdjustment


TWOPLACES = Decimal('0.01')


class PaymentAdjustmentService:
    DEFAULT_ADJUSTMENTS = {
        'online_card': Decimal('0.00'),
        'cash_on_delivery': Decimal('-10.00'),
        'card_on_delivery': Decimal('10.00'),
    }

    @classmethod
    def get_adjustment_percent(cls, payment_method):
        config = PaymentMethodAdjustment.objects.filter(
            payment_method=payment_method,
            is_active=True,
        ).first()
        if config:
            return config.adjustment_percent
        return cls.DEFAULT_ADJUSTMENTS.get(payment_method, Decimal('0.00'))

    @classmethod
    def apply_adjustment(cls, amount, payment_method):
        amount = Decimal(amount).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        adjustment_percent = cls.get_adjustment_percent(payment_method)
        adjustment_amount = (amount * adjustment_percent / Decimal('100')).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        adjusted_total = (amount + adjustment_amount).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

        discount_usd = Decimal('0.00')
        markup_usd = Decimal('0.00')
        if adjustment_amount < 0:
            discount_usd = abs(adjustment_amount)
        elif adjustment_amount > 0:
            markup_usd = adjustment_amount

        return {
            'adjustment_percent': adjustment_percent,
            'adjustment_amount': adjustment_amount,
            'discount_usd': discount_usd,
            'markup_usd': markup_usd,
            'adjusted_total_usd': adjusted_total,
        }
