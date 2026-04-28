from django.contrib import admin
from .models import Payment, PaymentWebhookEvent, CurrencyRate

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount_usd', 'currency', 'status', 'provider', 'created_at')
    list_filter = ('status', 'provider', 'method')
    search_fields = ('booking__public_number', 'provider_payment_id')

admin.site.register(PaymentWebhookEvent)
admin.site.register(CurrencyRate)
