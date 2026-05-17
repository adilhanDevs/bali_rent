from copy import deepcopy

from django.db.utils import OperationalError, ProgrammingError

from bali_rent.public_data import normalize_public_language

from .models import SiteContentEntry


def _set_nested_value(target, path, value):
    parts = [part for part in path.split('.') if part]
    if not parts:
        return

    cursor = target
    for part in parts[:-1]:
        next_value = cursor.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            cursor[part] = next_value
        cursor = next_value
    cursor[parts[-1]] = value


def _media_url(entry, request=None):
    if entry.media:
        if request:
            return request.build_absolute_uri(entry.media.url)
        return entry.media.url
    return entry.value.strip()


def _entry_value(entry, request=None):
    if entry.value_type == 'json':
        return deepcopy(entry.json_value)
    if entry.value_type in {'image', 'video', 'file'}:
        return _media_url(entry, request=request)
    return entry.value


def build_public_dictionary_overrides(lang, request=None):
    normalized = normalize_public_language(lang)

    try:
        shared_entries = list(SiteContentEntry.objects.filter(is_active=True, language='all').order_by('key'))
        localized_entries = list(SiteContentEntry.objects.filter(is_active=True, language=normalized).order_by('key'))
    except (OperationalError, ProgrammingError):
        return {}

    payload = {}
    for entry in shared_entries:
        _set_nested_value(payload, entry.key, _entry_value(entry, request=request))
    for entry in localized_entries:
        _set_nested_value(payload, entry.key, _entry_value(entry, request=request))
    return payload
