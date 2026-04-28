from rest_framework import serializers
from .models import (
    Season, ScooterSeasonPrice, OccupancyPricingRule, 
    DevicePricingRule, GeoPricingRule, PriceCalculationLog
)

# Public Serializers
class PricingCalculateSerializer(serializers.Serializer):
    vehicle_id = serializers.IntegerField()
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    addon_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    delivery_lat = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    delivery_lng = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    promo_code = serializers.CharField(required=False, allow_blank=True)
    device_platform = serializers.ChoiceField(choices=['ios', 'android', 'web'], required=False)
    user_country = serializers.CharField(max_length=2, required=False)

class PricingResponseSerializer(serializers.Serializer):
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    delivery_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    addons_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    price_calculation_id = serializers.IntegerField()

# Admin Serializers
class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = '__all__'

class ScooterSeasonPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScooterSeasonPrice
        fields = '__all__'

class OccupancyPricingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = OccupancyPricingRule
        fields = '__all__'

class DevicePricingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DevicePricingRule
        fields = '__all__'

class GeoPricingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeoPricingRule
        fields = '__all__'

class PriceCalculationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceCalculationLog
        fields = '__all__'
        read_only_fields = fields
