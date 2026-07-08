from rest_framework import serializers

from .models import SiteContentEntry
from .page_settings import PAGE_SETTINGS_KEYS, parse_page_settings_key, validate_page_settings_path


class SiteContentEntrySerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SiteContentEntry
        fields = (
            'id',
            'key',
            'language',
            'value_type',
            'value',
            'json_value',
            'media',
            'media_url',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'media_url', 'created_at', 'updated_at')

    def get_media_url(self, obj):
        if not obj.media:
            return ''

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.media.url)
        return obj.media.url

    def validate(self, attrs):
        attrs = super().validate(attrs)
        key = attrs.get('key', getattr(self.instance, 'key', ''))
        language = attrs.get('language', getattr(self.instance, 'language', ''))
        page_key, field_key = parse_page_settings_key(key)
        if page_key in PAGE_SETTINGS_KEYS and field_key == 'path':
            if language != 'all':
                raise serializers.ValidationError({'language': 'Page path must be shared across all languages.'})
            raw_value = attrs.get('value', getattr(self.instance, 'value', ''))
            attrs['value'] = validate_page_settings_path(
                raw_value,
                page_key=page_key,
                instance_pk=getattr(self.instance, 'pk', None),
            )
        return attrs
