from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=255)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    before_json = models.JSONField(default=dict, help_text="Snapshot before change")
    after_json = models.JSONField(default=dict, help_text="Snapshot after change")
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['content_type', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.action} on {self.content_type} {self.object_id} by {self.user}"

class AdminLoginLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    is_success = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Login for {self.user.email} at {self.created_at}"

class WebhookProcessingLog(models.Model):
    provider = models.CharField(max_length=50)
    event_id = models.CharField(max_length=255)
    event_type = models.CharField(max_length=100)
    payload_json = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=20, default='pending') # success, failure
    error_message = models.TextField(blank=True)

    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    processing_time_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('provider', 'event_id')
        indexes = [
            models.Index(fields=['provider', 'event_id']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['processed']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.provider} webhook {self.event_id}: {self.status}"
