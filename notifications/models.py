from django.db import models
from django.utils import timezone


class Notification(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    body = models.TextField()
    type = models.CharField(max_length=50, default='system')
    data_json = models.JSONField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['type']),
            models.Index(fields=['created_at']),
        ]

    def mark_as_read(self):
        if self.is_read:
            return
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])

    def __str__(self):
        return f'{self.title} -> {self.user.email}'


class NotificationLog(models.Model):
    STATUS_CHOICES = (
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    )
    CHANNEL_CHOICES = (
        ('in_app', 'In-App'),
        ('push', 'Push'),
    )

    notification = models.ForeignKey(
        Notification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notification_logs',
    )
    event_type = models.CharField(max_length=50, db_index=True)
    event_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='in_app')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    payload_json = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f'{self.event_type} [{self.status}]'


class NotificationTemplate(models.Model):
    code = models.CharField(max_length=100, unique=True)
    language = models.CharField(max_length=10)
    title_template = models.CharField(max_length=255)
    body_template = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code', 'language']

    def __str__(self):
        return f"{self.code} ({self.language})"
