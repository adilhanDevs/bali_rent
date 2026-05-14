from rest_framework import serializers

from .models import DeliveryZone, DeliveryZoneTranslation, LocationSection


class LocationSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationSection
        fields = ('id', 'language', 'title1', 'title2', 'description', 'map_eyebrow', 'map_region', 'is_active', 'updated_at')
        read_only_fields = ('id', 'updated_at')


class DeliveryZoneTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZoneTranslation
        fields = ('id', 'language', 'name')


class AdminDeliveryZoneSerializer(serializers.ModelSerializer):
    translations = DeliveryZoneTranslationSerializer(many=True, required=False)

    class Meta:
        model = DeliveryZone
        fields = ('id', 'name', 'is_free', 'is_active', 'translations')

    def update(self, instance, validated_data):
        translations_data = validated_data.pop('translations', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if translations_data is not None:
            for t in translations_data:
                DeliveryZoneTranslation.objects.update_or_create(
                    zone=instance,
                    language=t['language'],
                    defaults={'name': t['name']},
                )
        return instance
