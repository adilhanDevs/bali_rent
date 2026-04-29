from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Season(models.Model):
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=50, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    multiplier = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date', 'name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['start_date', 'end_date', 'is_active']),
        ]

    def __str__(self):
        return self.name


class ScooterSeasonPrice(models.Model):
    scooter = models.ForeignKey('catalog.Vehicle', on_delete=models.CASCADE, related_name='season_prices')
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='scooter_prices')
    price_per_day_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['season__start_date', 'scooter__title']
        constraints = [
            models.UniqueConstraint(fields=['scooter', 'season'], name='unique_scooter_season_price'),
        ]

    @property
    def price_per_day(self):
        return self.price_per_day_usd

    def __str__(self):
        return f"{self.scooter.title} in {self.season.name}: {self.price_per_day_usd}"


class OccupancyPricingRule(models.Model):
    threshold_percent = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    price_increase_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['threshold_percent']
        constraints = [
            models.UniqueConstraint(fields=['threshold_percent'], name='unique_occupancy_threshold'),
        ]

    @property
    def adjustment_percent(self):
        return self.price_increase_percent

    def __str__(self):
        sign = '+' if self.price_increase_percent >= 0 else ''
        return f"{self.threshold_percent}% -> {sign}{self.price_increase_percent}%"


class DevicePricingRule(models.Model):
    DEVICE_CHOICES = (
        ('ios', 'iOS'),
        ('android', 'Android'),
        ('web', 'Web'),
    )

    device_type = models.CharField(max_length=20, choices=DEVICE_CHOICES)
    country_code = models.CharField(max_length=2, blank=True, null=True, help_text='Optional ISO 3166-1 alpha-2')
    multiplier = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['device_type', 'country_code']
        constraints = [
            models.UniqueConstraint(fields=['device_type', 'country_code'], name='unique_device_country_pricing_rule'),
        ]

    @property
    def platform(self):
        return self.device_type

    @property
    def adjustment_percent(self):
        return (self.multiplier - Decimal('1.00')) * Decimal('100')

    def __str__(self):
        suffix = f" ({self.country_code})" if self.country_code else ""
        return f"{self.device_type}{suffix} x{self.multiplier}"


class GeoPricingRule(models.Model):
    country_code = models.CharField(max_length=2, help_text='ISO 3166-1 alpha-2')
    city = models.CharField(max_length=100, blank=True)
    multiplier = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['country_code', 'city']
        constraints = [
            models.UniqueConstraint(fields=['country_code', 'city'], name='unique_geo_pricing_rule'),
        ]

    @property
    def adjustment_percent(self):
        return (self.multiplier - Decimal('1.00')) * Decimal('100')

    def __str__(self):
        city_part = f" / {self.city}" if self.city else ""
        return f"{self.country_code}{city_part} x{self.multiplier}"


class PriceCalculationLog(models.Model):
    booking = models.OneToOneField(
        'bookings.Booking',
        on_delete=models.CASCADE,
        related_name='price_log',
        null=True,
        blank=True,
    )
    scooter = models.ForeignKey('catalog.Vehicle', on_delete=models.SET_NULL, null=True, related_name='price_logs')
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='price_logs')
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    final_price = models.DecimalField(max_digits=10, decimal_places=2)
    payload_json = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['scooter', 'created_at']),
        ]

    @property
    def total_price(self):
        return self.final_price

    @property
    def calculation_snapshot(self):
        return self.payload_json

    def __str__(self):
        return f"Calculation for {self.scooter} at {self.created_at}"
