from django.db import models

class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    booking = models.ForeignKey('bookings.Booking', on_delete=models.PROTECT, related_name='payments')
    provider = models.CharField(max_length=50) # stripe, xendit, etc.
    method = models.CharField(max_length=50) # card, crypto, bank_transfer
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2)
    amount_display = models.CharField(max_length=50)
    currency = models.CharField(max_length=10)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    provider_payment_id = models.CharField(max_length=255, blank=True)
    payment_url = models.URLField(max_length=500, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for {self.booking.public_number} ({self.status})"

class PaymentWebhookEvent(models.Model):
    provider = models.CharField(max_length=50)
    event_id = models.CharField(max_length=255)
    event_type = models.CharField(max_length=100)
    payload_json = models.JSONField()
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        unique_together = ('provider', 'event_id')

    def __str__(self):
        return f"{self.provider} event {self.event_id}"

class CurrencyRate(models.Model):
    base_currency = models.CharField(max_length=10, default='USD')
    target_currency = models.CharField(max_length=10)
    rate = models.DecimalField(max_digits=18, decimal_places=6)
    markup_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    source = models.CharField(max_length=100)
    fetched_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.base_currency} to {self.target_currency}: {self.rate}"
