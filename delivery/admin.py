from django.contrib import admin

from .models import DeliveryAddress, DeliveryPoint, DeliveryPricingRule, DeliveryZone, DeliveryZoneTranslation, LocationSection


class DeliveryPricingRuleInline(admin.TabularInline):
    model = DeliveryPricingRule
    extra = 0


class DeliveryZoneTranslationInline(admin.TabularInline):
    model = DeliveryZoneTranslation
    extra = 6
    fields = ('language', 'name')
    verbose_name = 'Zone name translation'
    verbose_name_plural = 'Zone name translations (en/ru/zh/id/de/fr)'


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_free', 'is_active', 'translations_count', 'center_lat', 'center_lng', 'radius_km')
    list_filter = ('is_free', 'is_active')
    search_fields = ('name',)
    inlines = [DeliveryPricingRuleInline, DeliveryZoneTranslationInline]

    def translations_count(self, obj):
        return obj.translations.count()
    translations_count.short_description = 'Translations'


@admin.register(LocationSection)
class LocationSectionAdmin(admin.ModelAdmin):
    list_display = ('language', 'title1', 'title2', 'is_active', 'updated_at')
    list_filter = ('is_active', 'language')
    search_fields = ('title1', 'title2', 'description')
    fieldsets = (
        (None, {
            'fields': ('language', 'is_active'),
        }),
        ('Section Heading', {
            'fields': ('title1', 'title2'),
            'description': 'Displayed as: "[title1]\\n[title2]" where title2 is highlighted in yellow.',
        }),
        ('Description', {
            'fields': ('description',),
        }),
        ('Map Overlay', {
            'fields': ('map_eyebrow', 'map_region'),
            'description': 'Small labels shown on the map tile. Example: eyebrow="REAL MAP · OPENSTREETMAP", region="South & Central Bali".',
            'classes': ('collapse',),
        }),
    )


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
