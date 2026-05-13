from django.contrib import admin
from .models import NewsArticle, NewsArticleTranslation


class NewsArticleTranslationInline(admin.TabularInline):
    model = NewsArticleTranslation
    extra = 1


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ('slug', 'published_at', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    prepopulated_fields = {'slug': ('slug',)}
    inlines = [NewsArticleTranslationInline]
