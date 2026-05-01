from django.contrib import admin

from .models import AdminLoginLog, AuditLog, WebhookProcessingLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'user', 'content_type', 'object_id')
    list_filter = ('action', 'content_type', 'created_at')
    search_fields = ('object_id', 'user__email')
    readonly_fields = ('created_at',)


@admin.register(AdminLoginLog)
class AdminLoginLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'ip_address', 'is_success')
    list_filter = ('is_success', 'created_at')
    search_fields = ('user__email', 'ip_address')
    readonly_fields = ('created_at',)


@admin.register(WebhookProcessingLog)
class WebhookProcessingLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'provider', 'event_type', 'event_id', 'status', 'processed', 'processing_time_ms')
    list_filter = ('provider', 'status', 'processed', 'created_at')
    search_fields = ('event_id', 'event_type', 'error_message')
    readonly_fields = ('created_at', 'processed_at')
