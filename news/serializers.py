from rest_framework import serializers
from .models import NewsArticle, NewsArticleTranslation


class NewsArticleTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsArticleTranslation
        fields = ('id', 'language', 'title', 'description')


class NewsArticleSerializer(serializers.ModelSerializer):
    translations = NewsArticleTranslationSerializer(many=True, read_only=True)
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = NewsArticle
        fields = ('id', 'slug', 'image', 'published_at', 'title', 'description', 'translations')

    def _lang(self):
        request = self.context.get('request')
        if request:
            return request.query_params.get('lang', 'en')
        return 'en'

    def get_title(self, obj):
        lang = self._lang()
        t = next((t for t in obj.translations.all() if t.language == lang), None)
        if not t:
            t = next((t for t in obj.translations.all() if t.language == 'en'), None)
        return t.title if t else ''

    def get_description(self, obj):
        lang = self._lang()
        t = next((t for t in obj.translations.all() if t.language == lang), None)
        if not t:
            t = next((t for t in obj.translations.all() if t.language == 'en'), None)
        return t.description if t else ''


class AdminNewsArticleSerializer(serializers.ModelSerializer):
    translations = NewsArticleTranslationSerializer(many=True, required=False)

    class Meta:
        model = NewsArticle
        fields = ('id', 'slug', 'image', 'published_at', 'is_active', 'sort_order', 'translations', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def create(self, validated_data):
        translations_data = validated_data.pop('translations', [])
        article = NewsArticle.objects.create(**validated_data)
        for t in translations_data:
            NewsArticleTranslation.objects.create(article=article, **t)
        return article

    def update(self, instance, validated_data):
        translations_data = validated_data.pop('translations', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if translations_data is not None:
            for t in translations_data:
                NewsArticleTranslation.objects.update_or_create(
                    article=instance,
                    language=t['language'],
                    defaults={'title': t['title'], 'description': t['description']},
                )
        return instance
