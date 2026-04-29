from django.db import models


class PaymentMethodAdjustment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('online_card', 'Online Card'),
        ('cash_on_delivery', 'Cash on Delivery'),
        ('card_on_delivery', 'Card on Delivery'),
    )

    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, unique=True)
    adjustment_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['payment_method']

    def __str__(self):
        return f'{self.payment_method}: {self.adjustment_percent}%'


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

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['provider']),
            models.Index(fields=['provider_payment_id']),
            models.Index(fields=['provider', 'provider_payment_id']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['booking', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Payment for {self.booking.public_number} ({self.status})"

class PaymentWebhookEvent(models.Model):
    # DEPRECATED: Use audit.WebhookProcessingLog instead for unified logging.
    provider = models.CharField(max_length=50)
    event_id = models.CharField(max_length=255)
    event_type = models.CharField(max_length=100)
    payload_json = models.JSONField()
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        unique_together = ('provider', 'event_id')
        indexes = [
            models.Index(fields=['provider', 'event_id']),
            models.Index(fields=['processed', 'processed_at']),
        ]

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
