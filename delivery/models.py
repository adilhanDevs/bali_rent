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
    is_free = models.BooleanField(db_column='free_delivery', default=False)
    is_active = models.BooleanField(default=True)

    # DEPRECATED Legacy/fallback fields kept for compatibility with older data and logic.
    # Do not use these in new logic. A migration plan should remove these in Phase 2.
    center_lat = models.FloatField(blank=True, null=True, help_text='DEPRECATED: Use polygon instead.')
    center_lng = models.FloatField(blank=True, null=True, help_text='DEPRECATED: Use polygon instead.')
    radius_km = models.FloatField(default=5.0, help_text='DEPRECATED: Use polygon instead.')
    polygon_json = models.JSONField(blank=True, null=True, help_text='DEPRECATED: Use polygon instead.')
    free_delivery = models.BooleanField(default=False, help_text='DEPRECATED: Use is_free instead.')
    base_price_usd = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    price_per_km_usd = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ['name']

    @property
    def polygon_json(self):
        return self.polygon

    @polygon_json.setter
    def polygon_json(self, value):
        self.polygon = value

    @property
    def free_delivery(self):
        return self.is_free

    @free_delivery.setter
    def free_delivery(self, value):
        self.is_free = value

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
