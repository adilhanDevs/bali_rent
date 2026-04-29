from django.contrib import admin

from .models import (
    DevicePricingRule,
    GeoPricingRule,
    OccupancyPricingRule,
    PriceCalculationLog,
    ScooterSeasonPrice,
    Season,
)


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'start_date', 'end_date', 'multiplier', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ('start_date', 'name')


@admin.register(ScooterSeasonPrice)
class ScooterSeasonPriceAdmin(admin.ModelAdmin):
    list_display = ('scooter', 'season', 'price_per_day_usd', 'updated_at')
    list_filter = ('season',)
    search_fields = ('scooter__title', 'scooter__sku', 'season__name', 'season__code')
    autocomplete_fields = ('scooter', 'season')
    ordering = ('season__start_date', 'scooter__title')


@admin.register(OccupancyPricingRule)
class OccupancyPricingRuleAdmin(admin.ModelAdmin):
    list_display = ('threshold_percent', 'price_increase_percent', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('threshold_percent',)
    ordering = ('threshold_percent',)


@admin.register(DevicePricingRule)
class DevicePricingRuleAdmin(admin.ModelAdmin):
    list_display = ('device_type', 'country_code', 'multiplier', 'is_active', 'updated_at')
    list_filter = ('device_type', 'country_code', 'is_active')
    search_fields = ('device_type', 'country_code')
    ordering = ('device_type', 'country_code')


@admin.register(GeoPricingRule)
class GeoPricingRuleAdmin(admin.ModelAdmin):
    list_display = ('country_code', 'city', 'multiplier', 'is_active', 'updated_at')
    list_filter = ('country_code', 'is_active')
    search_fields = ('country_code', 'city')
    ordering = ('country_code', 'city')


@admin.register(PriceCalculationLog)
class PriceCalculationLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'scooter', 'user', 'booking', 'base_price', 'final_price', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('scooter__title', 'scooter__sku', 'user__email', 'user__full_name', 'booking__public_number')
    autocomplete_fields = ('booking', 'scooter', 'user')
    readonly_fields = (
        'booking',
        'scooter',
        'user',
        'base_price',
        'final_price',
        'payload_json',
        'ip_address',
        'user_agent',
        'created_at',
    )
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
