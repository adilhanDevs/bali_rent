from django.contrib import admin
from .models import SupportTicket, SupportMessage, ExternalContactLink

class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 1

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'status', 'channel', 'created_at')
    list_filter = ('status', 'channel')
    search_fields = ('subject', 'user__email')
    inlines = [SupportMessageInline]

admin.site.register(ExternalContactLink)
