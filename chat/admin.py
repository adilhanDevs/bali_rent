from django.contrib import admin

from .models import ChatAttachment, ChatMessage, ChatParticipant, ChatThread, QuickReply


class ChatParticipantInline(admin.TabularInline):
    model = ChatParticipant
    extra = 0
    autocomplete_fields = ('user',)


class ChatAttachmentInline(admin.TabularInline):
    model = ChatAttachment
    extra = 0
    autocomplete_fields = ('uploaded_by',)
    readonly_fields = ('created_at',)


class ChatMessageInline(admin.StackedInline):
    model = ChatMessage
    extra = 0
    autocomplete_fields = ('sender',)
    readonly_fields = ('created_at', 'updated_at')
    show_change_link = True


class ChatAdminAccessMixin:
    def _can_view(self, request):
        user = request.user
        return user.is_authenticated and user.is_staff

    def _can_manage(self, request):
        user = request.user
        return user.is_superuser or user.role in {'admin', 'manager'}

    def has_module_permission(self, request):
        return self._can_view(request)

    def has_view_permission(self, request, obj=None):
        return self._can_view(request)

    def has_add_permission(self, request):
        return self._can_manage(request)

    def has_change_permission(self, request, obj=None):
        return self._can_manage(request)

    def has_delete_permission(self, request, obj=None):
        return self._can_manage(request)


@admin.register(ChatThread)
class ChatThreadAdmin(ChatAdminAccessMixin, admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'created_by', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'participants__user__full_name', 'participants__user__email', 'participants__user__phone')
    autocomplete_fields = ('created_by',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ChatParticipantInline, ChatMessageInline]


@admin.register(ChatParticipant)
class ChatParticipantAdmin(ChatAdminAccessMixin, admin.ModelAdmin):
    list_display = ('thread', 'user', 'role', 'joined_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('thread__title', 'user__full_name', 'user__email', 'user__phone')
    autocomplete_fields = ('thread', 'user')
    readonly_fields = ('joined_at',)


@admin.register(ChatMessage)
class ChatMessageAdmin(ChatAdminAccessMixin, admin.ModelAdmin):
    list_display = ('id', 'thread', 'sender', 'short_text', 'created_at')
    list_filter = ('created_at', 'thread__status')
    search_fields = ('text', 'sender__full_name', 'sender__email', 'thread__title')
    autocomplete_fields = ('thread', 'sender')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ChatAttachmentInline]

    def short_text(self, obj):
        return obj.text[:60]


@admin.register(ChatAttachment)
class ChatAttachmentAdmin(ChatAdminAccessMixin, admin.ModelAdmin):
    list_display = ('id', 'message', 'uploaded_by', 'original_name', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('original_name', 'uploaded_by__full_name', 'uploaded_by__email', 'message__thread__title')
    autocomplete_fields = ('message', 'uploaded_by')
    readonly_fields = ('created_at',)


@admin.register(QuickReply)
class QuickReplyAdmin(ChatAdminAccessMixin, admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_by', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'text', 'created_by__full_name', 'created_by__email')
    autocomplete_fields = ('created_by',)
    readonly_fields = ('created_at', 'updated_at')
