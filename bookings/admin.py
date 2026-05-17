from django.contrib import admin
from .models import Booking, BookingAddon, BookingStatusHistory, AvailabilityBlock

class BookingAddonInline(admin.TabularInline):
    model = BookingAddon
    extra = 0

class BookingStatusHistoryInline(admin.TabularInline):
    model = BookingStatusHistory
    extra = 0
    readonly_fields = ('created_at',)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('public_number', 'contact_name', 'contact_phone', 'user', 'vehicle', 'start_at', 'end_at', 'status', 'total_usd')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('public_number', 'contact_name', 'contact_phone', 'user__email', 'vehicle__sku')
    inlines = [BookingAddonInline, BookingStatusHistoryInline]
    readonly_fields = ('created_at',)

admin.site.register(AvailabilityBlock)
