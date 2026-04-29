from django.contrib import admin
from .models import Payment, PaymentWebhookEvent, CurrencyRate, PaymentMethodAdjustment


@admin.register(PaymentMethodAdjustment)
class PaymentMethodAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('payment_method', 'adjustment_percent', 'is_active', 'updated_at')
    list_filter = ('is_active', 'payment_method')
    search_fields = ('payment_method',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount_usd', 'currency', 'status', 'provider', 'created_at')
    list_filter = ('status', 'provider', 'method')
    search_fields = ('booking__public_number', 'provider_payment_id')

admin.site.register(PaymentWebhookEvent)
admin.site.register(CurrencyRate)
