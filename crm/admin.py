from django.contrib import admin

from .models import (
    CustomerInteraction,
    CustomerNote,
    CustomerProfile,
    CustomerSegment,
    DynamicPriceRule,
    PromoCode,
    SeasonPriceRule,
    StaffTask,
    TaskChecklistItem,
    TaskComment,
)


class CrmAccessMixin:
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


class CustomerNoteInline(admin.TabularInline):
    model = CustomerNote
    extra = 0
    fields = ('author', 'text', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

    def has_view_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.is_staff

    def has_add_permission(self, request, obj):
        return request.user.is_superuser or request.user.role in {'admin', 'manager'}

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.role in {'admin', 'manager'}

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.role in {'admin', 'manager'}


class TaskChecklistItemInline(admin.TabularInline):
    model = TaskChecklistItem
    extra = 0
    fields = ('title', 'is_completed', 'sort_order', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    fields = ('author', 'text', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('author',)


@admin.register(CustomerProfile)
class CustomerProfileAdmin(CrmAccessMixin, admin.ModelAdmin):
    list_display = ('display_name', 'email', 'phone', 'segment', 'created_at')
    list_filter = ('segment',)
    search_fields = ('user__full_name', 'user__email', 'user__phone')
    autocomplete_fields = ('user', 'segment')
    inlines = [CustomerNoteInline]
    readonly_fields = ('created_at', 'updated_at')

    def display_name(self, obj):
        return obj.user.full_name or obj.user.email

    def email(self, obj):
        return obj.user.email

    def phone(self, obj):
        return obj.user.phone


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(CrmAccessMixin, admin.ModelAdmin):
    list_display = ('name', 'code', 'discount_percent')
    search_fields = ('name', 'code')


@admin.register(CustomerNote)
class CustomerNoteAdmin(CrmAccessMixin, admin.ModelAdmin):
    list_display = ('customer', 'author', 'created_at')
    list_filter = ('author', 'created_at')
    search_fields = ('customer__user__full_name', 'customer__user__email', 'customer__user__phone', 'text')
    autocomplete_fields = ('customer', 'author')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(CustomerInteraction)
class CustomerInteractionAdmin(CrmAccessMixin, admin.ModelAdmin):
    list_display = ('customer', 'interaction_type', 'occurred_at', 'created_by')
    list_filter = ('interaction_type', 'occurred_at')
    search_fields = ('customer__user__full_name', 'customer__user__email', 'customer__user__phone', 'description')
    autocomplete_fields = ('customer', 'created_by')
    readonly_fields = ('created_at',)

@admin.register(StaffTask)
class StaffTaskAdmin(CrmAccessMixin, admin.ModelAdmin):
    list_display = ('title', 'status', 'assigned_to', 'related_booking', 'due_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('title',)
    autocomplete_fields = ('assigned_to', 'related_booking')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [TaskChecklistItemInline, TaskCommentInline]


@admin.register(TaskChecklistItem)
class TaskChecklistItemAdmin(CrmAccessMixin, admin.ModelAdmin):
    list_display = ('title', 'task', 'is_completed', 'sort_order', 'created_at')
    list_filter = ('is_completed',)
    search_fields = ('title', 'task__title')
    autocomplete_fields = ('task',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TaskComment)
class TaskCommentAdmin(CrmAccessMixin, admin.ModelAdmin):
    list_display = ('task', 'author', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('task__title', 'author__full_name', 'author__email', 'text')
    autocomplete_fields = ('task', 'author')
    readonly_fields = ('created_at', 'updated_at')


admin.site.register(PromoCode)
admin.site.register(SeasonPriceRule)
admin.site.register(DynamicPriceRule)
