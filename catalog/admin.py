from django.contrib import admin
from .models import VehicleType, VehicleModel, Vehicle, VehicleImage, VehicleTranslation, VehicleMaintenance

class VehicleImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 1

class VehicleTranslationInline(admin.TabularInline):
    model = VehicleTranslation
    extra = 1

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('title', 'sku', 'model', 'base_price_usd', 'status', 'is_featured')
    list_filter = ('status', 'is_featured', 'model__type')
    search_fields = ('title', 'sku', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [VehicleImageInline, VehicleTranslationInline]

admin.site.register(VehicleType)
admin.site.register(VehicleModel)
admin.site.register(VehicleMaintenance)
