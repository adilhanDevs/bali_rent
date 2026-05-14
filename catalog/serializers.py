from rest_framework import serializers
from .models import VehicleType, VehicleModel, Vehicle, VehicleImage, VehicleTranslation
from addons.models import Addon
from bookings.models import AvailabilityBlock
from django.db.models import Q

class VehicleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleType
        fields = ('id', 'code', 'name')

class VehicleModelSerializer(serializers.ModelSerializer):
    type_name = serializers.CharField(source='type.name', read_only=True)
    type_code = serializers.CharField(source='type.code', read_only=True)
    
    class Meta:
        model = VehicleModel
        fields = ('id', 'name', 'brand', 'type_name', 'type_code', 'engine_cc', 
                  'transmission', 'fuel_consumption', 'year', 'trunk', 
                  'helmets_count', 'description', 'rental_terms')

class ScooterImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleImage
        fields = ('id', 'image', 'alt_text', 'sort_order', 'is_main')

class ScooterListSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='model.type.name', read_only=True)
    engine_capacity = serializers.IntegerField(source='model.engine_cc', read_only=True)
    price_per_day = serializers.DecimalField(source='base_price_usd', max_digits=10, decimal_places=2, read_only=True)
    main_image = serializers.SerializerMethodField()
    short_description = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = ('id', 'title', 'slug', 'type', 'engine_capacity', 'price_per_day', 
                  'main_image', 'status', 'rating_avg', 'reviews_count', 
                  'short_description', 'is_available', 'is_featured')

    def get_main_image(self, obj):
        images = list(obj.images.all())
        main_img = next((image for image in images if image.is_main), None)
        if not main_img and images:
            main_img = images[0]
        if main_img:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(main_img.image.url)
            return main_img.image.url
        return None

    def get_short_description(self, obj):
        return obj.model.description[:100] + '...' if obj.model.description else ''

    def get_is_available(self, obj):
        if hasattr(obj, 'has_availability_conflict'):
            return not obj.has_availability_conflict
        request = self.context.get('request')
        if not request:
            return True
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            return not AvailabilityBlock.objects.filter(
                vehicle=obj,
                start_at__lt=end_date,
                end_at__gt=start_date
            ).exists()
        return True

class ScooterDetailSerializer(ScooterListSerializer):
    model_info = VehicleModelSerializer(source='model', read_only=True)
    gallery = ScooterImageSerializer(source='images', many=True, read_only=True)
    full_description = serializers.SerializerMethodField()
    characteristics = serializers.SerializerMethodField()
    rental_terms = serializers.SerializerMethodField()
    available_addons = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = ScooterListSerializer.Meta.fields + (
            'model_info', 'gallery', 'full_description', 'characteristics',
            'rental_terms', 'available_addons'
        )

    def _get_lang(self):
        request = self.context.get('request')
        return (request.GET.get('lang', 'en') if request else 'en') or 'en'

    def get_full_description(self, obj):
        lang = self._get_lang()
        translation = next((t for t in obj.translations.all() if t.language == lang), None)
        if translation and translation.description:
            return translation.description
        return obj.model.description

    def get_rental_terms(self, obj):
        lang = self._get_lang()
        translation = next((t for t in obj.translations.all() if t.language == lang), None)
        if translation and translation.rental_terms:
            return translation.rental_terms
        return obj.model.rental_terms

    def get_characteristics(self, obj):
        model = obj.model
        lang = self._get_lang()
        translation = next((t for t in obj.translations.all() if t.language == lang), None)
        return {
            'engine_cc': model.engine_cc,
            'transmission': (translation and translation.transmission) or model.transmission,
            'fuel_consumption': model.fuel_consumption,
            'year': model.year,
            'trunk': (translation and translation.trunk) or model.trunk,
            'helmets_count': model.helmets_count,
            'color': obj.color,
        }

    def get_available_addons(self, obj):
        from bali_rent.public_views import localized_addon_payload
        request = self.context.get('request') if hasattr(self, 'context') else None
        lang = (request.GET.get('lang') if request else None) or 'en'
        addons = Addon.objects.filter(is_active=True).prefetch_related('translations')
        return [localized_addon_payload(addon, lang) for addon in addons]


class AdminScooterSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='model.type.name', read_only=True)
    engine_capacity = serializers.IntegerField(source='model.engine_cc', read_only=True)
    price_per_day = serializers.DecimalField(source='base_price_usd', max_digits=10, decimal_places=2, read_only=True)
    main_image = serializers.SerializerMethodField()
    short_description = serializers.SerializerMethodField()
    model_info = VehicleModelSerializer(source='model', read_only=True)
    gallery = ScooterImageSerializer(source='images', many=True, read_only=True)
    full_description = serializers.CharField(source='model.description', read_only=True)
    characteristics = serializers.SerializerMethodField()
    rental_terms = serializers.CharField(source='model.rental_terms', read_only=True)
    translations = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = (
            'id', 'model', 'model_info', 'title', 'slug', 'sku', 'color',
            'base_price_usd', 'price_per_day', 'status', 'mileage', 'rating_avg',
            'reviews_count', 'is_featured', 'type', 'engine_capacity', 'main_image',
            'short_description', 'full_description', 'characteristics',
            'rental_terms', 'gallery', 'translations', 'created_at'
        )
        read_only_fields = (
            'id', 'price_per_day', 'rating_avg', 'reviews_count', 'type',
            'engine_capacity', 'main_image', 'short_description',
            'full_description', 'characteristics', 'rental_terms', 'gallery',
            'translations', 'model_info', 'created_at'
        )

    def get_main_image(self, obj):
        images = list(obj.images.all())
        main_img = next((image for image in images if image.is_main), None)
        if not main_img and images:
            main_img = images[0]
        if main_img:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(main_img.image.url)
            return main_img.image.url
        return None

    def get_short_description(self, obj):
        return obj.model.description[:100] + '...' if obj.model.description else ''

    def get_characteristics(self, obj):
        model = obj.model
        return {
            'engine_cc': model.engine_cc,
            'transmission': model.transmission,
            'fuel_consumption': model.fuel_consumption,
            'year': model.year,
            'trunk': model.trunk,
            'helmets_count': model.helmets_count,
            'color': obj.color,
        }

    def get_translations(self, obj):
        return [
            {
                'language': t.language,
                'title': t.title,
                'description': t.description,
                'rental_terms': t.rental_terms,
                'transmission': t.transmission or '',
                'trunk': t.trunk or '',
            }
            for t in obj.translations.all()
        ]
