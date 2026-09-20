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


CYRILLIC_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts',
    'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu',
    'я': 'ya',
}


def safe_slugify(text: str) -> str:
    if not text:
        return ''
    transliterated = ''.join(CYRILLIC_TO_LATIN.get(ch, ch) for ch in str(text).lower())
    return slugify(transliterated)


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
        translations = list(obj.translations.all())
        t = next((t for t in translations if t.language == lang), None)
        if not t and lang != 'en':
            t = next((t for t in translations if t.language == 'en'), None)
        if not t and translations:
            t = translations[0]
        return t.title if t else ''

    def get_description(self, obj):
        lang = self._lang()
        translations = list(obj.translations.all())
        t = next((t for t in translations if t.language == lang), None)
        if not t and lang != 'en':
            t = next((t for t in translations if t.language == 'en'), None)
        if not t and translations:
            t = translations[0]
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
            base_slug = safe_slugify(first_title)
            if not base_slug:
                base_slug = f"article-{uuid.uuid4().hex[:8]}"
            mutable_data['slug'] = base_slug
        else:
            clean_slug = safe_slugify(slug)
            if clean_slug:
                mutable_data['slug'] = clean_slug
            else:
                mutable_data['slug'] = f"article-{uuid.uuid4().hex[:8]}"

        # Ensure published_at
        if not mutable_data.get('published_at'):
            mutable_data['published_at'] = timezone.now().date().isoformat()

        # Ensure is_active default to True if omitted or empty
        if mutable_data.get('is_active') in ('', None):
            mutable_data['is_active'] = True

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
