from django.core.exceptions import ValidationError
from django.db import models


class ChatThread(models.Model):
    STATUS_OPEN = 'open'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = (
        (STATUS_OPEN, 'Open'),
        (STATUS_CLOSED, 'Closed'),
    )

    title = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_chat_threads',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-created_at']

    def __str__(self):
        return self.title or f'Chat #{self.pk}'


class ChatParticipant(models.Model):
    ROLE_CLIENT = 'client'
    ROLE_MANAGER = 'manager'
    ROLE_STAFF = 'staff'
    ROLE_CHOICES = (
        (ROLE_CLIENT, 'Client'),
        (ROLE_MANAGER, 'Manager'),
        (ROLE_STAFF, 'Staff'),
    )

    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='chat_participations')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('thread', 'user')
        ordering = ['joined_at', 'id']

    def __str__(self):
        return f'{self.user.email} in {self.thread}'


class ChatMessage(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='chat_messages')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'id']

    def clean(self):
        errors = {}
        if self.thread_id and self.sender_id:
            is_participant = ChatParticipant.objects.filter(thread_id=self.thread_id, user_id=self.sender_id).exists()
            if not is_participant:
                errors['sender'] = 'Sender must be a participant of the thread.'
        if not self.text:
            errors['text'] = 'Message text is required.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'Message #{self.pk} in {self.thread}'


class ChatAttachment(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='attachments')
    uploaded_by = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='chat_attachments')
    file = models.FileField(upload_to='chat_attachments/')
    original_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def clean(self):
        errors = {}
        if self.message_id and self.uploaded_by_id:
            is_participant = ChatParticipant.objects.filter(
                thread_id=self.message.thread_id,
                user_id=self.uploaded_by_id,
            ).exists()
            if not is_participant:
                errors['uploaded_by'] = 'Uploader must be a participant of the thread.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.file and not self.original_name:
            self.original_name = self.file.name
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.original_name or f'Attachment #{self.pk}'


class QuickReply(models.Model):
    title = models.CharField(max_length=100)
    text = models.TextField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quick_replies',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title
