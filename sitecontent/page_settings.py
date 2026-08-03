import re

from django.core.exceptions import ValidationError
from django.db.utils import OperationalError, ProgrammingError

from bali_rent.public_data import PUBLIC_LANGUAGES, normalize_public_language

from .models import SiteContentEntry


PAGE_SETTINGS_DEFINITIONS = (
    {"key": "home", "default_path": "/"},
    {"key": "catalog", "default_path": "/catalog"},
    {"key": "prices", "default_path": "/prices"},
    {"key": "how", "default_path": "/how-it-works"},
    {"key": "locations", "default_path": "/locations"},
    {"key": "contacts", "default_path": "/contacts"},
    {"key": "news", "default_path": "/news", "supports_children": True},
    {"key": "booking", "default_path": "/booking"},
    {"key": "payment", "default_path": "/payment"},
    {"key": "login", "default_path": "/login"},
    {"key": "register", "default_path": "/register"},
    {"key": "profile", "default_path": "/profile"},
)

PAGE_SETTINGS_KEYS = {item["key"] for item in PAGE_SETTINGS_DEFINITIONS}
PAGE_SETTINGS_DEFAULT_PATHS = {item["key"]: item["default_path"] for item in PAGE_SETTINGS_DEFINITIONS}
PAGE_SETTINGS_SUPPORTS_CHILDREN = {item["key"] for item in PAGE_SETTINGS_DEFINITIONS if item.get("supports_children")}
PAGE_SETTINGS_RESERVED_PREFIXES = ("/admin", "/_next", "/api")
PAGE_SETTINGS_KEY_RE = re.compile(r"^pageSettings\.([a-z0-9_]+)\.(title|path)$")


def parse_page_settings_key(key):
    match = PAGE_SETTINGS_KEY_RE.match(str(key or "").strip())
    if not match:
        return None, None
    return match.group(1), match.group(2)


def normalize_page_path(value):
    raw = str(value or "").strip()
    if not raw:
        return ""
    if "://" in raw or "?" in raw or "#" in raw:
        raise ValidationError("Page path must be a relative URL like /news.")
    if "[" in raw or "]" in raw:
        raise ValidationError("Dynamic route syntax is not allowed in page paths.")

    path = raw if raw.startswith("/") else f"/{raw}"
    path = re.sub(r"/{2,}", "/", path).strip()
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    if not re.fullmatch(r"/[A-Za-z0-9/_-]*", path):
        raise ValidationError("Use only letters, numbers, dash, underscore, and slash in page paths.")
    return path


def _path_conflicts_with_reserved_prefix(path):
    for prefix in PAGE_SETTINGS_RESERVED_PREFIXES:
        if path == prefix or path.startswith(f"{prefix}/"):
            return True
    return False


def validate_page_settings_path(value, *, page_key, instance_pk=None):
    normalized_path = normalize_page_path(value)
    if not normalized_path:
        raise ValidationError("Page path cannot be empty.")
    if _path_conflicts_with_reserved_prefix(normalized_path):
        raise ValidationError("This path is reserved by the application.")

    for other_page_key, default_path in PAGE_SETTINGS_DEFAULT_PATHS.items():
        if other_page_key != page_key and normalized_path == default_path:
            raise ValidationError(f'This path is already used by the "{other_page_key}" page.')

    try:
        existing_entries = SiteContentEntry.objects.filter(
            is_active=True,
            key__startswith="pageSettings.",
            key__endswith=".path",
        ).exclude(pk=instance_pk)
    except (OperationalError, ProgrammingError):
        return normalized_path

    for entry in existing_entries:
        other_page_key, other_field = parse_page_settings_key(entry.key)
        if other_field != "path" or not other_page_key:
            continue
        try:
            other_path = normalize_page_path(entry.value)
        except ValidationError:
            continue
        if other_path == normalized_path and other_page_key != page_key:
            raise ValidationError(f'This path is already assigned to the "{other_page_key}" page.')

    return normalized_path


def build_public_page_settings(lang):
    normalized_lang = normalize_public_language(lang)
    payload = {}

    try:
        shared_entries = list(
            SiteContentEntry.objects.filter(
                is_active=True,
                language="all",
                key__startswith="pageSettings.",
            ).order_by("key")
        )
        localized_entries = list(
            SiteContentEntry.objects.filter(
                is_active=True,
                language=normalized_lang,
                key__startswith="pageSettings.",
            ).order_by("key")
        )
    except (OperationalError, ProgrammingError):
        return payload

    for entry in shared_entries:
        page_key, field_key = parse_page_settings_key(entry.key)
        if not page_key or not field_key:
            continue
        page_payload = payload.setdefault(page_key, {})
        if field_key == "path":
            try:
                page_payload[field_key] = normalize_page_path(entry.value)
            except ValidationError:
                continue
        else:
            page_payload[field_key] = entry.value.strip()

    for entry in localized_entries:
        page_key, field_key = parse_page_settings_key(entry.key)
        if not page_key or field_key != "title":
            continue
        page_payload = payload.setdefault(page_key, {})
        page_payload[field_key] = entry.value.strip()

    return payload


def build_public_page_route_aliases():
    aliases = {}

    try:
        entries = list(
            SiteContentEntry.objects.filter(
                is_active=True,
                language="all",
                key__startswith="pageSettings.",
                key__endswith=".path",
            ).order_by("key", "language")
        )
    except (OperationalError, ProgrammingError):
        return aliases

    for entry in entries:
        page_key, field_key = parse_page_settings_key(entry.key)
        if field_key != "path" or not page_key:
            continue
        try:
            path = normalize_page_path(entry.value)
        except ValidationError:
            continue
        if not path or path == PAGE_SETTINGS_DEFAULT_PATHS.get(page_key):
            continue
        aliases[path] = page_key

    return aliases


def get_public_page_languages():
    return [item["api_code"] for item in PUBLIC_LANGUAGES]
