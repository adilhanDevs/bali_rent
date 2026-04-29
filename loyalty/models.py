from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class LoyaltyProgram(models.Model):
    name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class LoyaltyTier(models.Model):
    program = models.ForeignKey(LoyaltyProgram, on_delete=models.CASCADE, related_name='tiers')
    name = models.CharField(max_length=100)
    min_points = models.IntegerField()
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        ordering = ['program__name', 'min_points']
        unique_together = ('program', 'name')

    def clean(self):
        errors = {}
        if self.min_points < 0:
            errors['min_points'] = 'Minimum points must be greater than or equal to 0.'
        if self.discount_percent < 0:
            errors['discount_percent'] = 'Discount percent must be greater than or equal to 0.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.program.name} - {self.name}'


class CustomerLoyaltyAccount(models.Model):
    customer = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='loyalty_accounts')
    program = models.ForeignKey(LoyaltyProgram, on_delete=models.CASCADE, related_name='accounts')
    points = models.IntegerField(default=0)
    tier = models.ForeignKey(LoyaltyTier, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounts')

    class Meta:
        ordering = ['customer__email', 'program__name']
        unique_together = ('customer', 'program')

    def clean(self):
        errors = {}
        if self.points < 0:
            errors['points'] = 'Points must be greater than or equal to 0.'
        if self.tier and self.tier.program_id != self.program_id:
            errors['tier'] = 'Tier must belong to the same loyalty program.'
        if errors:
            raise ValidationError(errors)

    def update_tier(self, commit=True):
        new_tier = (
            LoyaltyTier.objects.filter(program=self.program, min_points__lte=self.points)
            .order_by('-min_points')
            .first()
        )
        self.tier = new_tier
        if commit and self.pk:
            type(self).objects.filter(pk=self.pk).update(tier=new_tier)
        return new_tier

    def save(self, *args, **kwargs):
        self.full_clean()
        self.update_tier(commit=False)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.customer.email} - {self.program.name}'


class LoyaltyTransaction(models.Model):
    TYPE_EARN = 'earn'
    TYPE_SPEND = 'spend'
    TYPE_CHOICES = (
        (TYPE_EARN, 'Earn'),
        (TYPE_SPEND, 'Spend'),
    )

    account = models.ForeignKey(CustomerLoyaltyAccount, on_delete=models.CASCADE, related_name='transactions')
    points = models.IntegerField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']

    def clean(self):
        errors = {}
        if self.points < 0:
            errors['points'] = 'Points must be greater than or equal to 0.'
        if self.type not in {self.TYPE_EARN, self.TYPE_SPEND}:
            errors['type'] = 'Invalid transaction type.'
        if errors:
            raise ValidationError(errors)

    def signed_points(self):
        return self.points if self.type == self.TYPE_EARN else -self.points

    def _apply_balance_change(self, *args, **kwargs):
        with transaction.atomic():
            account = CustomerLoyaltyAccount.objects.select_for_update().select_related('program').get(pk=self.account_id)
            old_signed_points = 0

            if self.pk:
                previous = type(self).objects.get(pk=self.pk)
                old_signed_points = previous.signed_points()

            new_balance = account.points - old_signed_points + self.signed_points()
            if new_balance < 0:
                raise ValidationError({'points': 'Spend transaction cannot make account points negative.'})

            account.points = new_balance
            account.save()
            return super().save(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        return self._apply_balance_change(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            account = CustomerLoyaltyAccount.objects.select_for_update().select_related('program').get(pk=self.account_id)
            new_balance = account.points - self.signed_points()
            if new_balance < 0:
                raise ValidationError({'points': 'Deleting this transaction would make account points negative.'})
            account.points = new_balance
            account.save()
            return super().delete(*args, **kwargs)

    def __str__(self):
        return f'{self.account} - {self.type} {self.points}'


class ReferralCode(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='referral_codes')
    code = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.code

class Referral(models.Model):
    referrer = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='sent_referrals')
    referred_user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='received_referrals',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Referral from {self.referrer}'
