from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('client', 'Client'),
        ('staff', 'Staff'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    )
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    admin_permissions = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Use email as username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    country = models.CharField(max_length=100, blank=True)
    preferred_language = models.CharField(max_length=10, default='en')
    preferred_currency = models.CharField(max_length=10, default='USD')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    marketing_accepted = models.BooleanField(default=False)

    def __str__(self):
        return f"Profile of {self.user.email}"

class UserDevice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    fcm_token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=50) # ios, android
    device_id = models.CharField(max_length=255)
    app_version = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.platform} device of {self.user.email}"

class SocialAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=50) # google, apple
    provider_user_id = models.CharField(max_length=255)
    email = models.EmailField()
    raw_data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.provider} account of {self.user.email}"
