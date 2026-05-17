from django.db import models


LANGUAGE_CHOICES = [
    ('all', 'All languages'),
    ('en', 'English'),
    ('ru', 'Русский'),
    ('zh', '中文'),
    ('id', 'Indonesia'),
    ('de', 'Deutsch'),
    ('fr', 'Français'),
]


class SiteContentEntry(models.Model):
    VALUE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('textarea', 'Textarea'),
        ('json', 'JSON'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('file', 'File'),
    ]

    key = models.CharField(max_length=255, help_text='Dot path, e.g. nav.catalog or media.home.heroVideo')
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    value_type = models.CharField(max_length=20, choices=VALUE_TYPE_CHOICES, default='text')
    value = models.TextField(blank=True, default='', help_text='Text value or external media URL fallback.')
    json_value = models.JSONField(blank=True, null=True)
    media = models.FileField(upload_to='site_content/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['key', 'language']
        unique_together = ('key', 'language')
        verbose_name = 'Site content entry'
        verbose_name_plural = 'Site content entries'

    def __str__(self):
        return f'{self.key} [{self.language}]'

