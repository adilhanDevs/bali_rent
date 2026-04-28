from django.db import models
from django.conf import settings

class PromotionCampaign(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['start_date', 'end_date', 'is_active']),
        ]

    def __str__(self):
        return self.name

class PromoCode(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('PERCENT', 'Percentage'),
        ('FIXED', 'Fixed Amount (USD)'),
    )
    campaign = models.ForeignKey(PromotionCampaign, on_delete=models.CASCADE, related_name='promo_codes', null=True, blank=True)
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    
    usage_limit = models.IntegerField(default=1)
    current_usage = models.IntegerField(default=0)
    
    min_booking_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['code', 'is_active']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]

    def __str__(self):
        return self.code

class Banner(models.Model):
    POSITION_CHOICES = (
        ('home_top', 'Home Top'),
        ('catalog_middle', 'Catalog Middle'),
        ('booking_success', 'Booking Success'),
    )
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to='banners/')
    link_url = models.URLField(blank=True)
    position = models.CharField(max_length=50, choices=POSITION_CHOICES)
    priority = models.IntegerField(default=0)
    
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'created_at']
        indexes = [
            models.Index(fields=['position', 'is_active']),
        ]

    def __str__(self):
        return self.title

class Referral(models.Model):
    # Temporary to fix imports
    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
