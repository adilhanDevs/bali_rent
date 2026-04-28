from django.db import models

class CustomerSegment(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return self.name

class PromoCode(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    usage_limit = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

class StaffTask(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    assigned_to = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='assigned_tasks')
    related_booking = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class SeasonPriceRule(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    multiplier = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class DynamicPriceRule(models.Model):
    rule_type = models.CharField(max_length=100)
    condition_json = models.JSONField()
    action_json = models.JSONField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.rule_type
