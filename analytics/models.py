from django.db import models
from django.conf import settings

class AnalyticsEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    device_id = models.CharField(max_length=255, blank=True, null=True)
    
    event_name = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_name', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['session_id', 'created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.event_name} at {self.created_at}"
