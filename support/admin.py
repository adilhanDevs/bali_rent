from django.contrib import admin
from .models import SupportTicket, SupportMessage, ExternalContactLink, FAQItem, FAQItemTranslation

class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 1


class FAQItemTranslationInline(admin.TabularInline):
    model = FAQItemTranslation
    extra = 6
    fields = ('language', 'question', 'answer')
    classes = ('collapse',)

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'status', 'channel', 'created_at')
    list_filter = ('status', 'channel')
    search_fields = ('subject', 'user__email', 'user__full_name', 'user__phone')
    inlines = [SupportMessageInline]


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'sender', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('message', 'ticket__subject', 'sender__email', 'sender__full_name')


@admin.register(ExternalContactLink)
class ExternalContactLinkAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'is_active', 'sort_order')
    list_filter = ('is_active',)
    search_fields = ('title', 'code', 'phone')


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ('code', 'is_active', 'sort_order', 'translations_count', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('code',)
    ordering = ('sort_order', 'id')
    inlines = [FAQItemTranslationInline]

    def translations_count(self, obj):
        return obj.translations.count()
    translations_count.short_description = 'Translations'
