from django.db import models


class NewsArticle(models.Model):
    slug = models.SlugField(max_length=200, unique=True)
    image = models.ImageField(upload_to='news/', blank=True, null=True)
    published_at = models.DateField()
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-id']

    def __str__(self):
        return self.slug


class NewsArticleTranslation(models.Model):
    article = models.ForeignKey(NewsArticle, on_delete=models.CASCADE, related_name='translations')
    language = models.CharField(max_length=10)
    title = models.CharField(max_length=255)
    description = models.TextField()

    class Meta:
        ordering = ['article_id', 'language']
        unique_together = ('article', 'language')

    def __str__(self):
        return f'{self.language} · {self.title}'
