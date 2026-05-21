from django.db.utils import DatabaseError

from bali_rent.public_data import normalize_public_language

from .translation_support import vehicle_type_translation_table_available


def language_candidates(lang):
    normalized = normalize_public_language(lang)
    short = normalized.split('-')[0]
    candidates = []
    for value in (normalized, short, 'en'):
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def _normalized_translation_language(value):
    raw = str(value or '').strip().lower().replace('_', '-')
    if not raw:
        return ''
    return normalize_public_language(raw)


def get_vehicle_translation(vehicle, lang):
    try:
        translations = list(vehicle.translations.all())
    except DatabaseError:
        return None

    for candidate in language_candidates(lang):
        translation = next(
            (item for item in translations if _normalized_translation_language(item.language) == candidate),
            None,
        )
        if translation is not None:
            return translation
    return None


def get_vehicle_type_name(vehicle_type, lang, fallback=None):
    default_name = fallback or vehicle_type.name
    if not vehicle_type_translation_table_available():
        return default_name

    try:
        translations = list(vehicle_type.translations.all())
    except DatabaseError:
        return default_name

    for candidate in language_candidates(lang):
        translation = next(
            (item for item in translations if _normalized_translation_language(item.language) == candidate),
            None,
        )
        if translation and translation.name:
            return translation.name
    return default_name
