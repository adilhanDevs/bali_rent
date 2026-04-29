from django.contrib import admin
from .models import Notification, NotificationLog, NotificationTemplate


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'type', 'is_read', 'sent_at', 'created_at')
    list_filter = ('is_read', 'type', 'created_at')
    search_fields = ('title', 'body', 'user__email', 'user__full_name', 'user__phone')
    autocomplete_fields = ('user',)
    readonly_fields = ('sent_at', 'read_at', 'created_at')
    ordering = ('-created_at',)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'user', 'status', 'channel', 'event_key', 'created_at')
    list_filter = ('event_type', 'status', 'channel', 'created_at')
    search_fields = ('event_key', 'user__email', 'notification__title', 'error_message')
    autocomplete_fields = ('user', 'notification')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('code', 'language', 'is_active')
    list_filter = ('language', 'is_active')
    search_fields = ('code', 'title_template', 'body_template')
