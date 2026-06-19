from rest_framework import serializers
from .models import VehicleType, VehicleTypeTranslation, VehicleModel, Vehicle, VehicleImage, VehicleTranslation
from addons.models import Addon
from bookings.models import AvailabilityBlock
from django.db.models import Q
from django.db.utils import DatabaseError
from django.utils.text import slugify
from bali_rent.public_data import normalize_public_language
from .localization import get_vehicle_translation, get_vehicle_type_name
from .translation_support import vehicle_type_translation_table_available
from pricing.serializers import PublicScooterRentalRateSerializer, ScooterRentalRateSerializer
from pricing.services import PricingCalculationService

class VehicleTypeTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleTypeTranslation
        fields = ('language', 'name')


class VehicleTypeSerializer(serializers.ModelSerializer):
    translations = serializers.SerializerMethodField()
    code = serializers.CharField(required=False, allow_blank=True)

    def get_translations(self, obj):
        if not vehicle_type_translation_table_available():
            return []
        try:
            return VehicleTypeTranslationSerializer(obj.translations.all(), many=True).data
        except DatabaseError:
            return []

    def _build_unique_code(self, name, instance=None):
        base_code = slugify(name).replace('-', '_') or 'category'
        code = base_code
        counter = 2

        queryset = VehicleType.objects.all()
        if instance is not None:
            queryset = queryset.exclude(pk=instance.pk)

        while queryset.filter(code=code).exists():
            code = f'{base_code}_{counter}'
            counter += 1
        return code

    def validate(self, attrs):
        name = attrs.get('name') or getattr(self.instance, 'name', '')
        code = attrs.get('code')

        if not code and name:
            attrs['code'] = self._build_unique_code(name=name, instance=self.instance)

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request:
            lang = normalize_public_language(
                request.GET.get('lang')
                or request.headers.get('X-Language')
                or request.headers.get('Accept-Language')
                or 'en'
            )
            data['name'] = get_vehicle_type_name(instance, lang, fallback=instance.name)
        return data

    class Meta:
        model = VehicleType
        fields = ('id', 'code', 'name', 'translations')

class VehicleModelSerializer(serializers.ModelSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=VehicleType.objects.all())
    type_name = serializers.SerializerMethodField()
    type_code = serializers.CharField(source='type.code', read_only=True)

    def get_type_name(self, obj):
        request = self.context.get('request')
        if not request:
            return obj.type.name
        lang = normalize_public_language(
            request.GET.get('lang')
            or request.headers.get('X-Language')
            or request.headers.get('Accept-Language')
            or 'en'
        )
        return get_vehicle_type_name(obj.type, lang, fallback=obj.type.name)
    
    class Meta:
        model = VehicleModel
        fields = ('id', 'name', 'brand', 'type', 'type_name', 'type_code', 'engine_cc', 
                  'transmission', 'fuel_consumption', 'year', 'trunk', 
                  'helmets_count', 'description', 'rental_terms')

class ScooterImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        return obj.image.url if obj.image else None

    class Meta:
        model = VehicleImage
        fields = ('id', 'image', 'alt_text', 'sort_order', 'is_main')

class ScooterListSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    type_code = serializers.CharField(source='model.type.code', read_only=True)
    engine_capacity = serializers.IntegerField(source='model.engine_cc', read_only=True)
    price_per_day = serializers.SerializerMethodField()
    main_image = serializers.SerializerMethodField()
    short_description = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = ('id', 'title', 'slug', 'type', 'type_code', 'engine_capacity', 'price_per_day', 
                  'main_image', 'status', 'rating_avg', 'reviews_count', 
                  'short_description', 'is_available', 'is_featured')

    def get_main_image(self, obj):
        images = list(obj.images.all())
        main_img = next((image for image in images if image.is_main), None)
        if not main_img and images:
            main_img = images[0]
        if main_img:
            return main_img.image.url
        return None

    def _get_lang(self):
        request = self.context.get('request')
        if not request:
            return 'en'
        return normalize_public_language(
            request.GET.get('lang')
            or request.headers.get('X-Language')
            or request.headers.get('Accept-Language')
            or 'en'
        )

    def get_title(self, obj):
        translation = get_vehicle_translation(obj, self._get_lang())
        if translation and translation.title:
            return translation.title
        return obj.title

    def get_type(self, obj):
        return get_vehicle_type_name(obj.model.type, self._get_lang(), fallback=obj.model.type.name)

    def get_short_description(self, obj):
        translation = get_vehicle_translation(obj, self._get_lang())
        description = (
            translation.description
            if translation and translation.description
            else obj.model.description
        )
        return f'{description[:100]}...' if description else ''

    def get_price_per_day(self, obj):
        return PricingCalculationService.get_min_display_price(obj)

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
    pricing_tiers = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = ScooterListSerializer.Meta.fields + (
            'model_info', 'gallery', 'full_description', 'characteristics',
            'rental_terms', 'available_addons', 'pricing_tiers'
        )

    def get_full_description(self, obj):
        translation = get_vehicle_translation(obj, self._get_lang())
        if translation and translation.description:
            return translation.description
        return obj.model.description

    def get_rental_terms(self, obj):
        translation = get_vehicle_translation(obj, self._get_lang())
        if translation and translation.rental_terms:
            return translation.rental_terms
        return obj.model.rental_terms

    def get_characteristics(self, obj):
        model = obj.model
        translation = get_vehicle_translation(obj, self._get_lang())
        return {
            'engine_cc': model.engine_cc,
            'transmission': (translation and translation.transmission) or model.transmission,
            'fuel_consumption': model.fuel_consumption,
            'year': model.year,
            'trunk': (translation and translation.trunk) or model.trunk,
            'helmets_count': model.helmets_count,
            'color': (translation and translation.color) or obj.color,
        }

    def get_available_addons(self, obj):
        from bali_rent.public_views import localized_addon_payload
        lang = self._get_lang()
        addons = Addon.objects.filter(is_active=True).prefetch_related('translations')
        return [localized_addon_payload(addon, lang) for addon in addons]

    def get_pricing_tiers(self, obj):
        rates = PricingCalculationService._get_rental_rates(obj)
        return PublicScooterRentalRateSerializer(rates, many=True).data


class AdminScooterSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='model.type.name', read_only=True)
    engine_capacity = serializers.IntegerField(source='model.engine_cc', read_only=True)
    price_per_day = serializers.SerializerMethodField()
    main_image = serializers.SerializerMethodField()
    short_description = serializers.SerializerMethodField()
    model_info = VehicleModelSerializer(source='model', read_only=True)
    gallery = ScooterImageSerializer(source='images', many=True, read_only=True)
    full_description = serializers.CharField(source='model.description', read_only=True)
    characteristics = serializers.SerializerMethodField()
    rental_terms = serializers.CharField(source='model.rental_terms', read_only=True)
    translations = serializers.SerializerMethodField()
    pricing_tiers = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = (
            'id', 'model', 'model_info', 'title', 'slug', 'sku', 'color',
            'base_price_usd', 'price_per_day', 'status', 'mileage', 'rating_avg',
            'reviews_count', 'is_featured', 'type', 'engine_capacity', 'main_image',
            'short_description', 'full_description', 'characteristics',
            'rental_terms', 'gallery', 'translations', 'pricing_tiers', 'created_at'
        )
        read_only_fields = (
            'id', 'price_per_day', 'rating_avg', 'reviews_count', 'type',
            'engine_capacity', 'main_image', 'short_description',
            'full_description', 'characteristics', 'rental_terms', 'gallery',
            'translations', 'pricing_tiers', 'model_info', 'created_at'
        )

    def get_price_per_day(self, obj):
        return PricingCalculationService.get_min_display_price(obj)

    def get_main_image(self, obj):
        images = list(obj.images.all())
        main_img = next((image for image in images if image.is_main), None)
        if not main_img and images:
            main_img = images[0]
        if main_img:
            return main_img.image.url
        return None

    def get_short_description(self, obj):
        return obj.model.description[:100] + '...' if obj.model.description else ''

    def get_pricing_tiers(self, obj):
        rates = PricingCalculationService._get_rental_rates(obj)
        return ScooterRentalRateSerializer(rates, many=True).data

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
                'color': t.color or '',
            }
            for t in obj.translations.all()
        ]
