from django.db import transaction

from loyalty.models import Referral, ReferralCode


class ReferralService:
    @staticmethod
    def normalize_code(code):
        return str(code or '').strip().upper()

    @staticmethod
    def get_referral_code(code):
        normalized_code = ReferralService.normalize_code(code)
        if not normalized_code:
            return None
        return ReferralCode.objects.select_related('user').filter(code__iexact=normalized_code).first()

    @staticmethod
    @transaction.atomic
    def create_referral(referrer, referred_user=None):
        if referred_user is not None and referrer.pk == referred_user.pk:
            raise ValueError('A user cannot refer themselves.')
        referral, _created = Referral.objects.get_or_create(
            referrer=referrer,
            referred_user=referred_user,
        )
        return referral

    @staticmethod
    @transaction.atomic
    def create_referral_from_code(code, referred_user=None):
        referral_code = ReferralService.get_referral_code(code)
        if not referral_code:
            raise ValueError('Invalid referral code')
        return ReferralService.create_referral(referral_code.user, referred_user)
