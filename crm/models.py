from django.db import models
from django.utils import timezone

class CustomerSegment(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class CustomerProfile(models.Model):
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, related_name='customer_profile')
    segment = models.ForeignKey(CustomerSegment, on_delete=models.SET_NULL, null=True, blank=True, related_name='customers')
    avg_rating = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__full_name', 'user__email']

    def __str__(self):
        return self.user.full_name or self.user.email


class CustomerNote(models.Model):
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='customer_notes')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        customer_name = self.customer.user.full_name or self.customer.user.email
        return f'Note for {customer_name}'


class CustomerInteraction(models.Model):
    INTERACTION_TYPE_CHOICES = (
        ('call', 'Call'),
        ('email', 'Email'),
        ('chat', 'Chat'),
        ('booking', 'Booking'),
        ('payment', 'Payment'),
        ('support', 'Support'),
        ('review', 'Review'),
        ('other', 'Other'),
    )
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=30, choices=INTERACTION_TYPE_CHOICES, default='other')
    description = models.TextField()
    occurred_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logged_customer_interactions',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-occurred_at', '-created_at']

    def __str__(self):
        customer_name = self.customer.user.full_name or self.customer.user.email
        return f'{self.get_interaction_type_display()} for {customer_name}'

class StaffTask(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    assigned_to = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    related_booking = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        now = timezone.now()
        if self.due_at and self.due_at < now:
            errors['due_at'] = 'Due date cannot be in the past.'

        previous_status = None
        if self.pk:
            previous_status = type(self).objects.filter(pk=self.pk).values_list('status', flat=True).first()

        allowed_transitions = {
            'pending': {'pending', 'in_progress', 'cancelled'},
            'in_progress': {'in_progress', 'completed', 'cancelled'},
            'completed': {'completed'},
            'cancelled': {'cancelled'},
        }

        if previous_status is None:
            if self.status not in {'pending'}:
                errors['status'] = 'New tasks must start in pending status.'
        elif self.status not in allowed_transitions.get(previous_status, {previous_status}):
            errors['status'] = f'Cannot transition task from {previous_status} to {self.status}.'

        if self.status == 'completed' and self.pk:
            has_incomplete_items = self.checklist_items.filter(is_completed=False).exists()
            if has_incomplete_items:
                errors['status'] = 'All checklist items must be completed before finishing the task.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class TaskChecklistItem(models.Model):
    task = models.ForeignKey(StaffTask, on_delete=models.CASCADE, related_name='checklist_items')
    title = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.task_id and self.task.status == 'completed' and not self.is_completed:
            raise ValidationError({'is_completed': 'Checklist items for completed tasks must remain completed.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class TaskComment(models.Model):
    task = models.ForeignKey(StaffTask, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='task_comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'id']

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'Comment on {self.task}'

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
