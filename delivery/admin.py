from django.contrib import admin

from .models import DeliveryAddress, DeliveryPoint, DeliveryPricingRule, DeliveryZone


class DeliveryPricingRuleInline(admin.TabularInline):
    model = DeliveryPricingRule
    extra = 0


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_free', 'is_active', 'center_lat', 'center_lng', 'radius_km')
    list_filter = ('is_free', 'is_active')
    search_fields = ('name',)
    inlines = [DeliveryPricingRuleInline]


@admin.register(DeliveryPricingRule)
class DeliveryPricingRuleAdmin(admin.ModelAdmin):
    list_display = ('zone', 'price', 'is_active', 'created_at')
    list_filter = ('is_active', 'zone')
    search_fields = ('zone__name',)


@admin.register(DeliveryPoint)
class DeliveryPointAdmin(admin.ModelAdmin):
    list_display = ('address', 'lat', 'lng', 'created_at')
    search_fields = ('address',)


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ('address_text', 'user', 'lat', 'lng')
    search_fields = ('address_text', 'user__email', 'user__full_name')
