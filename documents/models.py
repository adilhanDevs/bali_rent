from django.db import models

class UserDocument(models.Model):
    STATUS_CHOICES = (
        ('not_uploaded', 'Not Uploaded'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    DOCUMENT_TYPE_CHOICES = (
        ('passport', 'Passport'),
        ('driver_license', 'Driver License'),
        ('selfie', 'Selfie'),
    )
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to='user_documents/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='reviewed_documents')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.document_type} of {self.user.email}"
