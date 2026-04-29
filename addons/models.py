from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Addon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    price_type = models.CharField(max_length=50) # per_day, per_booking
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.name

class AddonTranslation(models.Model):
    addon = models.ForeignKey(Addon, on_delete=models.CASCADE, related_name='translations')
    language = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    description = models.TextField()

    class Meta:
        unique_together = ('addon', 'language')

    def __str__(self):
        return f"{self.language} translation for {self.addon.name}"
