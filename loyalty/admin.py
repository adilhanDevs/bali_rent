from django.contrib import admin

from .models import (
    CustomerLoyaltyAccount,
    LoyaltyProgram,
    LoyaltyTier,
    LoyaltyTransaction,
    ReferralCode,
)


class LoyaltyTransactionInline(admin.TabularInline):
    model = LoyaltyTransaction
    extra = 0
    readonly_fields = ('created_at',)


class LoyaltyAdminAccessMixin:
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


@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(LoyaltyAdminAccessMixin, admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(LoyaltyTier)
class LoyaltyTierAdmin(LoyaltyAdminAccessMixin, admin.ModelAdmin):
    list_display = ('name', 'program', 'min_points', 'discount_percent')
    list_filter = ('program',)
    search_fields = ('name', 'program__name')
    autocomplete_fields = ('program',)


@admin.register(CustomerLoyaltyAccount)
class CustomerLoyaltyAccountAdmin(LoyaltyAdminAccessMixin, admin.ModelAdmin):
    list_display = ('customer', 'program', 'points', 'tier')
    list_filter = ('program', 'tier')
    search_fields = ('customer__full_name', 'customer__email', 'customer__phone', 'program__name', 'tier__name')
    autocomplete_fields = ('customer', 'program', 'tier')
    inlines = [LoyaltyTransactionInline]


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(LoyaltyAdminAccessMixin, admin.ModelAdmin):
    list_display = ('account', 'type', 'points', 'created_at')
    list_filter = ('type', 'account__program')
    search_fields = ('account__customer__full_name', 'account__customer__email', 'account__program__name')
    autocomplete_fields = ('account',)
    readonly_fields = ('created_at',)


@admin.register(ReferralCode)
class ReferralCodeAdmin(LoyaltyAdminAccessMixin, admin.ModelAdmin):
    list_display = ('code', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('code', 'user__full_name', 'user__email', 'user__phone')
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at',)
