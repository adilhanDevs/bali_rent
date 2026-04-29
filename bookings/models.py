from django.db import models

class Booking(models.Model):
    STATUS_CHOICES = (
        ('created', 'Created'),
        ('pending_payment', 'Pending Payment'),
        ('paid', 'Paid'),
        ('confirmed', 'Confirmed'),
        ('delivery', 'Delivery'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    public_number = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='bookings')
    vehicle = models.ForeignKey('catalog.Vehicle', on_delete=models.PROTECT, related_name='bookings')
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    delivery_address = models.ForeignKey('delivery.DeliveryAddress', on_delete=models.SET_NULL, null=True, blank=True)
    delivery_time = models.DateTimeField(null=True, blank=True)
    delivery_price_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=50) # online_card, cash_on_delivery, card_on_delivery
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    currency = models.CharField(max_length=10, default='USD')
    subtotal_usd = models.DecimalField(max_digits=10, decimal_places=2)
    addons_total_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    markup_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_usd = models.DecimalField(max_digits=10, decimal_places=2)
    total_display = models.CharField(max_length=50) # formatted total in selected currency
    pricing_snapshot_json = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['vehicle', 'start_at', 'end_at']),
        ]

    def __str__(self):
        return self.public_number

class BookingAddon(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='addons')
    addon = models.ForeignKey('addons.Addon', on_delete=models.PROTECT)
    name_snapshot = models.CharField(max_length=100)
    price_usd_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.name_snapshot} for {self.booking.public_number}"

class BookingStatusHistory(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.public_number}: {self.old_status} -> {self.new_status}"

class AvailabilityBlock(models.Model):
    TYPE_CHOICES = (
        ('booking', 'Booking'),
        ('maintenance', 'Maintenance'),
        ('manual_block', 'Manual Block'),
    )
    vehicle = models.ForeignKey('catalog.Vehicle', on_delete=models.CASCADE, related_name='availability_blocks')
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    source_booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True, related_name='availability_blocks')
    comment = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['vehicle', 'start_at', 'end_at']),
        ]

    def __str__(self):
        return f"Block for {self.vehicle.sku} ({self.start_at} - {self.end_at})"
