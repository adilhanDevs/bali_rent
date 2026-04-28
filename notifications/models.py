from django.db import models

class Notification(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    body = models.TextField()
    type = models.CharField(max_length=50) # booking_confirmed, payment_failed, etc.
    data_json = models.JSONField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class NotificationTemplate(models.Model):
    code = models.CharField(max_length=100, unique=True)
    language = models.CharField(max_length=10)
    title_template = models.CharField(max_length=255)
    body_template = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} ({self.language})"
