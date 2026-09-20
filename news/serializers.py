import json
import uuid
from django.utils.text import slugify
from django.utils import timezone
from rest_framework import serializers
from .models import NewsArticle, NewsArticleTranslation, NewsArticleImage


class NewsArticleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsArticleImage
        fields = ('id', 'image', 'alt_text', 'sort_order')


class NewsArticleTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsArticleTranslation
        fields = ('id', 'language', 'title', 'description')


class NewsArticleSerializer(serializers.ModelSerializer):
    translations = NewsArticleTranslationSerializer(many=True, read_only=True)
    images = NewsArticleImageSerializer(many=True, read_only=True)
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = NewsArticle
        fields = ('id', 'slug', 'image', 'images', 'published_at', 'title', 'description', 'translations')

    def _lang(self):
        request = self.context.get('request')
        supported = {'en', 'ru', 'zh', 'id', 'de', 'fr'}
        if request:
            raw = (
                request.query_params.get('lang')
                or request.headers.get('X-Language')
                or request.headers.get('Accept-Language')
                or 'en'
            )
            lang = str(raw).split(',')[0].strip().lower().replace('_', '-')
            base = lang.split('-')[0]
            if lang in supported:
                return lang
            if base in supported:
                return base
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
    images = NewsArticleImageSerializer(many=True, read_only=True)

    class Meta:
        model = NewsArticle
        fields = ('id', 'slug', 'image', 'images', 'published_at', 'is_active', 'sort_order', 'translations', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def to_internal_value(self, data):
        # Create a mutable copy if data is QueryDict / dict
        if hasattr(data, 'dict'):
            mutable_data = data.dict()
        elif isinstance(data, dict):
            mutable_data = data.copy()
        else:
            mutable_data = dict(data)

        # Handle translations sent as JSON string in multipart/form-data
        raw_translations = mutable_data.get('translations')
        if isinstance(raw_translations, str):
            try:
                mutable_data['translations'] = json.loads(raw_translations)
            except (ValueError, TypeError):
                mutable_data['translations'] = []

        # Ensure slug exists or auto-generate
        slug = str(mutable_data.get('slug') or '').strip()
        if not slug:
            translations = mutable_data.get('translations') or []
            first_title = ''
            if isinstance(translations, list) and translations:
                first_title = str(translations[0].get('title', '')).strip()
            base_slug = slugify(first_title) if first_title else ''
            if not base_slug:
                base_slug = f"article-{uuid.uuid4().hex[:8]}"
            mutable_data['slug'] = base_slug
        else:
            # Ensure slug conforms to slug format
            clean_slug = slugify(slug)
            if clean_slug:
                mutable_data['slug'] = clean_slug

        # Ensure published_at
        if not mutable_data.get('published_at'):
            mutable_data['published_at'] = timezone.now().date().isoformat()

        return super().to_internal_value(mutable_data)

    def create(self, validated_data):
        translations_data = validated_data.pop('translations', [])
        request = self.context.get('request')
        
        # Check if multiple images were provided in request.FILES
        gallery_files = []
        if request and hasattr(request, 'FILES'):
            gallery_files = request.FILES.getlist('images')

        # If primary image not set but images were uploaded, use the first one
        if not validated_data.get('image') and gallery_files:
            validated_data['image'] = gallery_files[0]

        article = NewsArticle.objects.create(**validated_data)

        for t in translations_data:
            NewsArticleTranslation.objects.create(article=article, **t)

        for idx, file_obj in enumerate(gallery_files):
            NewsArticleImage.objects.create(
                article=article,
                image=file_obj,
                sort_order=idx,
            )

        return article

    def update(self, instance, validated_data):
        translations_data = validated_data.pop('translations', None)
        request = self.context.get('request')

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Check for new gallery files
        if request and hasattr(request, 'FILES'):
            gallery_files = request.FILES.getlist('images')
            if gallery_files:
                if not instance.image:
                    instance.image = gallery_files[0]
                current_count = instance.images.count()
                for idx, file_obj in enumerate(gallery_files):
                    NewsArticleImage.objects.create(
                        article=instance,
                        image=file_obj,
                        sort_order=current_count + idx,
                    )

        instance.save()

        if translations_data is not None:
            for t in translations_data:
                NewsArticleTranslation.objects.update_or_create(
                    article=instance,
                    language=t['language'],
                    defaults={'title': t['title'], 'description': t['description']},
                )
        return instance
