from django.contrib import admin
from .models import Addon, AddonTranslation

class AddonTranslationInline(admin.TabularInline):
    model = AddonTranslation
    extra = 1

@admin.register(Addon)
class AddonAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'price_usd', 'price_type', 'is_active')
    list_filter = ('is_active', 'price_type')
    search_fields = ('name', 'code')
    inlines = [AddonTranslationInline]
