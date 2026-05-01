from rest_framework import serializers
from django.utils.text import slugify

from .models import (
    DevicePricingRule,
    GeoPricingRule,
    OccupancyPricingRule,
    PriceCalculationLog,
    ScooterSeasonPrice,
    Season,
)
from django.utils import timezone
from datetime import timedelta


class PricingCalculateSerializer(serializers.Serializer):
    scooter_id = serializers.IntegerField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    device_type = serializers.ChoiceField(choices=['ios', 'android', 'web'], required=False, allow_null=True)
    country_code = serializers.CharField(max_length=2, required=False, allow_blank=True, allow_null=True)

    # Legacy aliases kept for compatibility with earlier project tests/integrations.
    vehicle_id = serializers.IntegerField(required=False, write_only=True)
    start_at = serializers.DateTimeField(required=False, write_only=True)
    end_at = serializers.DateTimeField(required=False, write_only=True)
    device_platform = serializers.ChoiceField(choices=['ios', 'android', 'web'], required=False, allow_null=True, write_only=True)
    user_country = serializers.CharField(max_length=2, required=False, allow_blank=True, allow_null=True, write_only=True)

    def validate(self, attrs):
        # Handle aliases
        scooter_id = attrs.get('scooter_id') or attrs.get('vehicle_id')
        start_at = attrs.get('start_at')
        end_at = attrs.get('end_at')
        
        # If datetime objects are provided, convert to dates for start_date/end_date
        start_date = attrs.get('start_date') or (start_at.date() if start_at else None)
        end_date = attrs.get('end_date') or (end_at.date() if end_at else None)
        
        device_type = attrs.get('device_type') or attrs.get('device_platform')
        country_code = attrs.get('country_code') or attrs.get('user_country')

        if scooter_id is None:
            raise serializers.ValidationError({'scooter_id': 'This field is required.'})
        if start_date is None:
            raise serializers.ValidationError({'start_date': 'This field is required.'})
        if end_date is None:
            raise serializers.ValidationError({'end_date': 'This field is required.'})
        
        if end_date < start_date:
            raise serializers.ValidationError({'end_date': 'end_date must be greater than or equal to start_date.'})

        # Logic from second validate method
        if start_at and end_at:
            if start_at >= end_at:
                raise serializers.ValidationError("end_at must be after start_at")
            if start_at < timezone.now() - timedelta(minutes=5): # Small buffer for tests/latency
                raise serializers.ValidationError("start_at cannot be in the past")

        attrs['scooter_id'] = scooter_id
        attrs['start_date'] = start_date
        attrs['end_date'] = end_date
        attrs['device_type'] = device_type
        attrs['country_code'] = country_code.upper() if country_code else None
        return attrs

class PricingResponseSerializer(serializers.Serializer):
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    season_adjustment = serializers.DecimalField(max_digits=10, decimal_places=2)
    occupancy_adjustment = serializers.DecimalField(max_digits=10, decimal_places=2)
    device_adjustment = serializers.DecimalField(max_digits=10, decimal_places=2)
    geo_adjustment = serializers.DecimalField(max_digits=10, decimal_places=2)
    final_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    price_calculation_id = serializers.IntegerField()


class SeasonSerializer(serializers.ModelSerializer):
    code = serializers.SlugField(required=False, allow_blank=True)

    class Meta:
        model = Season
        fields = '__all__'

    def _build_unique_code(self, name, instance=None):
        base_code = slugify(name) or 'season'
        code = base_code
        counter = 1
        queryset = Season.objects.all()
        if instance is not None:
            queryset = queryset.exclude(pk=instance.pk)
        while queryset.filter(code=code).exists():
            code = f'{base_code}-{counter}'
            counter += 1
        return code

    def validate(self, attrs):
        attrs = super().validate(attrs)
        name = attrs.get('name') or getattr(self.instance, 'name', '')
        code = attrs.get('code')
        if not code and name:
            attrs['code'] = self._build_unique_code(name=name, instance=self.instance)
        return attrs


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
        read_only_fields = (
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
