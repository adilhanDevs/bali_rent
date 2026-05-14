from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class DeliveryZone(models.Model):
    name = models.CharField(max_length=100)
    polygon = models.JSONField(
        db_column='polygon_json',
        blank=True,
        null=True,
        help_text='List of points: [{"lat": ..., "lng": ...}, ...]',
    )
    is_free = models.BooleanField(
        db_column='free_delivery',
        default=False,
        help_text='Use this flag for flat free-delivery zones.',
    )
    is_active = models.BooleanField(default=True)

    # DEPRECATED legacy/fallback fields kept for compatibility with older data and logic.
    center_lat = models.FloatField(blank=True, null=True, help_text='DEPRECATED: Use polygon instead.')
    center_lng = models.FloatField(blank=True, null=True, help_text='DEPRECATED: Use polygon instead.')
    radius_km = models.FloatField(default=5.0, help_text='DEPRECATED: Use polygon instead.')
    base_price_usd = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    price_per_km_usd = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class DeliveryPoint(models.Model):
    address = models.TextField()
    lat = models.FloatField()
    lng = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.address[:50]


class DeliveryPricingRule(models.Model):
    zone = models.ForeignKey(DeliveryZone, on_delete=models.CASCADE, related_name='pricing_rules')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['zone__name', '-is_active', '-created_at']

    def __str__(self):
        return f'{self.zone.name}: {self.price}'


class DeliveryZoneTranslation(models.Model):
    zone = models.ForeignKey(DeliveryZone, on_delete=models.CASCADE, related_name='translations')
    language = models.CharField(max_length=10)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['zone', 'language']
        unique_together = ('zone', 'language')

    def __str__(self):
        return f'{self.zone.name} ({self.language}): {self.name}'


class LocationSection(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('ru', 'Русский'),
        ('zh', '中文'),
        ('id', 'Indonesia'),
        ('de', 'Deutsch'),
        ('fr', 'Français'),
    ]
    language = models.CharField(max_length=10, unique=True, choices=LANGUAGE_CHOICES)
    title1 = models.CharField(max_length=200, blank=True, help_text='First line of section heading')
    title2 = models.CharField(max_length=200, blank=True, help_text='Second line (highlighted in yellow)')
    description = models.TextField(blank=True, help_text='Paragraph under the heading')
    map_eyebrow = models.CharField(max_length=200, blank=True, help_text='Small label above map region name')
    map_region = models.CharField(max_length=200, blank=True, help_text='Region name on the map overlay')
    zones_label = models.CharField(max_length=200, blank=True, help_text='Eyebrow above zones grid, e.g. "01 / 02 · ZONES"')
    zones_title = models.CharField(max_length=200, blank=True, help_text='Heading above zones grid, e.g. "Our delivery zones."')
    zones_desc = models.TextField(blank=True, help_text='Description paragraph above zones grid')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['language']
        verbose_name = 'Location Section Content'
        verbose_name_plural = 'Location Section Content'

    def __str__(self):
        return f'Location Section ({self.language})'


class DeliveryAddress(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='delivery_addresses', null=True, blank=True)
    address_text = models.TextField()
    lat = models.FloatField()
    lng = models.FloatField()
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.address_text[:50]
