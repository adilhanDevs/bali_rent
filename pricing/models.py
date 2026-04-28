from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Season(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['start_date', 'end_date', 'is_active']),
        ]

    def __str__(self):
        return self.name

class ScooterSeasonPrice(models.Model):
    scooter = models.ForeignKey('catalog.Vehicle', on_delete=models.CASCADE, related_name='season_prices')
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='scooter_prices')
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('scooter', 'season')

    def __str__(self):
        return f"{self.scooter.title} in {self.season.name}: {self.price_per_day}"

class OccupancyPricingRule(models.Model):
    name = models.CharField(max_length=100)
    min_occupancy_percent = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    max_occupancy_percent = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    adjustment_percent = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.min_occupancy_percent}% - {self.max_occupancy_percent}%)"

class DevicePricingRule(models.Model):
    PLATFORM_CHOICES = (
        ('ios', 'iOS'),
        ('android', 'Android'),
        ('web', 'Web'),
    )
    name = models.CharField(max_length=100)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    adjustment_percent = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} for {self.platform}"

class GeoPricingRule(models.Model):
    name = models.CharField(max_length=100)
    country_code = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2")
    adjustment_percent = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} for {self.country_code}"

class PricingRule(models.Model):
    # Temporary to fix imports
    name = models.CharField(max_length=100)

class PriceCalculationLog(models.Model):
    booking = models.OneToOneField('bookings.Booking', on_delete=models.CASCADE, related_name='price_log', null=True, blank=True)
    scooter = models.ForeignKey('catalog.Vehicle', on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    
    calculation_snapshot = models.JSONField(help_text="Full breakdown of price calculation")
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['scooter', 'created_at']),
        ]

    def __str__(self):
        return f"Calculation for {self.scooter} at {self.created_at}"
