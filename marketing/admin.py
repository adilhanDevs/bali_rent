from django.contrib import admin

from .models import Banner, PromoCode, PromoCodeRedemption, PromotionCampaign


class PromoCodeRedemptionInline(admin.TabularInline):
    model = PromoCodeRedemption
    extra = 0
    autocomplete_fields = ('user', 'booking')
    readonly_fields = ('created_at',)


@admin.register(PromotionCampaign)
class PromotionCampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'starts_at', 'ends_at', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ('-starts_at', 'name')


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'campaign',
        'discount_type',
        'discount_value',
        'usage_limit',
        'current_usage',
        'is_active',
    )
    list_filter = ('discount_type', 'is_active', 'campaign')
    search_fields = ('code', 'campaign__name', 'campaign__code')
    autocomplete_fields = ('campaign',)
    inlines = [PromoCodeRedemptionInline]
    ordering = ('code',)


@admin.register(PromoCodeRedemption)
class PromoCodeRedemptionAdmin(admin.ModelAdmin):
    list_display = ('promo_code', 'user', 'booking', 'discount_amount', 'created_at')
    list_filter = ('promo_code', 'created_at')
    search_fields = ('promo_code__code', 'user__email', 'user__full_name', 'booking__public_number')
    autocomplete_fields = ('promo_code', 'user', 'booking')
    ordering = ('-created_at',)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'placement', 'priority', 'starts_at', 'ends_at', 'is_active')
    list_filter = ('placement', 'is_active')
    search_fields = ('title', 'link_url')
    ordering = ('-priority', '-starts_at', 'title')
