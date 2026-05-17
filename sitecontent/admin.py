from django.contrib import admin

from .models import SiteContentEntry


@admin.register(SiteContentEntry)
class SiteContentEntryAdmin(admin.ModelAdmin):
    list_display = ('key', 'language', 'value_type', 'is_active', 'updated_at')
    list_filter = ('language', 'value_type', 'is_active')
    search_fields = ('key', 'value')
    ordering = ('key', 'language')

