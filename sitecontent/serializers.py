from rest_framework import serializers

from .models import SiteContentEntry


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

