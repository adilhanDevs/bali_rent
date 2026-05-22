from django.contrib import admin
from .models import VehicleType, VehicleTypeTranslation, VehicleModel, Vehicle, VehicleImage, VehicleTranslation, VehicleMaintenance

class VehicleImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 1

class VehicleTranslationInline(admin.TabularInline):
    model = VehicleTranslation
    extra = 1


class VehicleTypeTranslationInline(admin.TabularInline):
    model = VehicleTypeTranslation
    extra = 1

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('title', 'sku', 'model', 'base_price_usd', 'status', 'is_featured')
    list_filter = ('status', 'is_featured', 'model__type')
    search_fields = ('title', 'sku', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [VehicleImageInline, VehicleTranslationInline]

@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')
    inlines = [VehicleTypeTranslationInline]


admin.site.register(VehicleModel)
admin.site.register(VehicleMaintenance)
