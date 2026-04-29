from django.contrib import admin
from .models import SupportTicket, SupportMessage, ExternalContactLink, FAQItem, FAQItemTranslation

class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 1


class FAQItemTranslationInline(admin.TabularInline):
    model = FAQItemTranslation
    extra = 1

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'status', 'channel', 'created_at')
    list_filter = ('status', 'channel')
    search_fields = ('subject', 'user__email')
    inlines = [SupportMessageInline]


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ('code', 'is_active', 'sort_order', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('code', 'translations__question', 'translations__answer')
    inlines = [FAQItemTranslationInline]

admin.site.register(ExternalContactLink)
