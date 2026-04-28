from django.db import models
from django.conf import settings

class CryptoCurrency(models.Model):
    code = models.CharField(max_length=20, unique=True, help_text="BTC, ETH, USDT, etc.")
    name = models.CharField(max_length=100)
    network = models.CharField(max_length=100, help_text="ERC20, TRC20, BEP20, etc.")
    is_active = models.BooleanField(default=True)
    precision = models.IntegerField(default=8)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} ({self.network})"

class CryptoInvoice(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    booking = models.ForeignKey('bookings.Booking', on_delete=models.CASCADE, related_name='crypto_invoices')
    currency = models.ForeignKey(CryptoCurrency, on_delete=models.PROTECT)
    
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2)
    amount_crypto = models.DecimalField(max_digits=36, decimal_places=18)
    
    address = models.CharField(max_length=255)
    payment_url = models.URLField(max_length=500, blank=True)
    
    provider = models.CharField(max_length=50)
    provider_invoice_id = models.CharField(max_length=255, unique=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    expires_at = models.DateTimeField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['provider_invoice_id']),
            models.Index(fields=['status']),
            models.Index(fields=['address']),
        ]

    def __str__(self):
        return f"Invoice {self.provider_invoice_id} for {self.booking.public_number}"

class CryptoWebhookEvent(models.Model):
    provider = models.CharField(max_length=50)
    external_event_id = models.CharField(max_length=255, unique=True, help_text="For idempotency")
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['provider', 'external_event_id']),
        ]

    def __str__(self):
        return f"{self.provider} event {self.external_event_id}"
