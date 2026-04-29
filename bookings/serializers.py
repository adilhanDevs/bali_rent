from rest_framework import serializers
from .models import Booking, BookingAddon
from catalog.models import Vehicle
from addons.models import Addon
from .services import BookingPriceService, BookingAvailabilityService
from django.utils import timezone

class BookingAddonSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='addon.id')
    name = serializers.CharField(source='name_snapshot')
    price = serializers.DecimalField(source='price_usd_snapshot', max_digits=10, decimal_places=2)

    class Meta:
        model = BookingAddon
        fields = ['id', 'name', 'price', 'quantity']

class BookingSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='public_number')
    scooter = serializers.SerializerMethodField()
    start_datetime = serializers.DateTimeField(source='start_at')
    end_datetime = serializers.DateTimeField(source='end_at')
    rental_days = serializers.SerializerMethodField()
    delivery_address = serializers.CharField(source='delivery_address.address_text', allow_null=True)
    delivery_coordinates = serializers.SerializerMethodField()
    add_ons = BookingAddonSerializer(many=True, source='addons')
    base_price = serializers.DecimalField(source='subtotal_usd', max_digits=10, decimal_places=2)
    add_ons_price = serializers.DecimalField(source='addons_total_usd', max_digits=10, decimal_places=2)
    delivery_price = serializers.DecimalField(source='delivery_price_usd', max_digits=10, decimal_places=2)
    discount_amount = serializers.DecimalField(source='discount_usd', max_digits=10, decimal_places=2)
    markup_amount = serializers.DecimalField(source='markup_usd', max_digits=10, decimal_places=2)
    total_price = serializers.DecimalField(source='total_usd', max_digits=10, decimal_places=2)
    user = serializers.EmailField(source='user.email')

    class Meta:
        model = Booking
        fields = [
            'id', 'order_number', 'user', 'scooter', 'start_datetime', 'end_datetime',
            'rental_days', 'delivery_address', 'delivery_coordinates', 'add_ons',
            'base_price', 'add_ons_price', 'delivery_price', 'discount_amount',
            'markup_amount', 'total_price', 'currency', 'payment_method',
            'payment_status', 'status', 'created_at'
        ]

    def get_scooter(self, obj):
        return {
            'id': obj.vehicle.id,
            'title': obj.vehicle.title,
            'sku': obj.vehicle.sku
        }

    def get_rental_days(self, obj):
        return BookingPriceService.calculate_rental_days(obj.start_at, obj.end_at)

    def get_delivery_coordinates(self, obj):
        if obj.delivery_address:
            return {
                'latitude': obj.delivery_address.lat,
                'longitude': obj.delivery_address.lng
            }
        return None

class BookingCalculateSerializer(serializers.Serializer):
    scooter_id = serializers.IntegerField()
    start_datetime = serializers.DateTimeField()
    end_datetime = serializers.DateTimeField()
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    delivery_latitude = serializers.FloatField(required=False)
    delivery_longitude = serializers.FloatField(required=False)
    add_on_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    promo_code = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(choices=['online_card', 'cash_on_delivery', 'card_on_delivery'], default='online_card')
    currency = serializers.CharField(default='USD')

    def validate(self, data):
        if data['start_datetime'] >= data['end_datetime']:
            raise serializers.ValidationError("End datetime must be after start datetime.")
        
        if data['start_datetime'] < timezone.now():
            raise serializers.ValidationError("Start datetime cannot be in the past.")
            
        try:
            vehicle = Vehicle.objects.get(id=data['scooter_id'])
        except Vehicle.DoesNotExist:
            raise serializers.ValidationError("Scooter not found.")
            
        if not BookingAvailabilityService.is_available(vehicle, data['start_datetime'], data['end_datetime']):
            raise serializers.ValidationError("Scooter is not available for selected dates.")
            
        return data

class BookingCreateSerializer(BookingCalculateSerializer):
    def create(self, validated_data):
        # This will be handled in the view using BookingCreationService
        pass
