from django.contrib import admin
from .models import SupportTicket, SupportMessage, ExternalContactLink

class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 1

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
