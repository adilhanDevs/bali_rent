from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class PromotionCampaign(models.Model):
    name = models.CharField(max_length=255)
    code = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-starts_at', 'name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['starts_at', 'ends_at', 'is_active']),
        ]

    @property
    def start_date(self):
        return self.starts_at

    @start_date.setter
    def start_date(self, value):
        self.starts_at = value

    @property
    def end_date(self):
        return self.ends_at

    @end_date.setter
    def end_date(self, value):
        self.ends_at = value

    def __str__(self):
        return self.name


class PromoCode(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('PERCENT', 'Percentage'),
        ('FIXED', 'Fixed Amount'),
    )

    campaign = models.ForeignKey(
        PromotionCampaign,
        on_delete=models.CASCADE,
        related_name='promo_codes',
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(default=1)
    current_usage = models.PositiveIntegerField(default=0)
    min_booking_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        indexes = [
            models.Index(fields=['code', 'is_active']),
            models.Index(fields=['is_active', 'starts_at', 'ends_at']),
            models.Index(fields=['starts_at', 'ends_at']),
        ]

    @property
    def value(self):
        return self.discount_value

    @value.setter
    def value(self, new_value):
        self.discount_value = new_value

    @property
    def valid_from(self):
        return self.starts_at or (self.campaign.starts_at if self.campaign_id else None)

    @valid_from.setter
    def valid_from(self, value):
        self.starts_at = value

    @property
    def valid_until(self):
        return self.ends_at or (self.campaign.ends_at if self.campaign_id else None)

    @valid_until.setter
    def valid_until(self, value):
        self.ends_at = value

    def __str__(self):
        return self.code


class PromoCodeRedemption(models.Model):
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name='redemptions')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promo_code_redemptions',
    )
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promo_code_redemptions',
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['promo_code', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f'{self.promo_code.code} redemption'


class Banner(models.Model):
    PLACEMENT_CHOICES = (
        ('home_top', 'Home Top'),
        ('catalog_middle', 'Catalog Middle'),
        ('booking_success', 'Booking Success'),
    )

    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to='banners/')
    link_url = models.URLField(blank=True)
    placement = models.CharField(max_length=50, choices=PLACEMENT_CHOICES)
    priority = models.IntegerField(default=0)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', '-starts_at', 'title']
        indexes = [
            models.Index(fields=['placement', 'is_active']),
            models.Index(fields=['starts_at', 'ends_at']),
        ]

    @property
    def position(self):
        return self.placement

    @position.setter
    def position(self, value):
        self.placement = value

    @property
    def start_date(self):
        return self.starts_at

    @start_date.setter
    def start_date(self, value):
        self.starts_at = value

    @property
    def end_date(self):
        return self.ends_at

    @end_date.setter
    def end_date(self, value):
        self.ends_at = value

    def __str__(self):
        return self.title


# Referral model moved to loyalty app.
