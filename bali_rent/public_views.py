from decimal import Decimal

from django.db.utils import OperationalError, ProgrammingError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from addons.models import Addon
from catalog.models import Vehicle
from delivery.models import DeliveryZone
from support.models import FAQItem

from .public_data import (
    ACCENT_BY_SLUG,
    ZONE_MINUTES,
    get_addon_copy,
    get_public_languages,
    get_public_site_content,
    get_vehicle_copy,
    normalize_public_language,
)


USD_TO_IDR = Decimal("15500")
DEFAULT_DELIVERY_SLOTS = ["09:00", "12:00", "16:00", "19:00"]


ADDON_META = {
    "helmet_full": {"icon": "⛑️", "category": "safety"},
    "insurance": {"icon": "🛡️", "category": "safety"},
    "gps": {"icon": "📍", "category": "tech"},
    "raincoat": {"icon": "🧥", "category": "comfort"},
    "phone_mount": {"icon": "📱", "category": "tech"},
    "wifi": {"icon": "📶", "category": "tech"},
    "helmet_open": {"icon": "🪖", "category": "safety"},
    "bag": {"icon": "🎒", "category": "comfort"},
}


def usd_to_idr(value):
    if value is None:
        return 0
    amount = Decimal(str(value))
    return int((amount * USD_TO_IDR).quantize(Decimal("1")))


def vehicle_deposit(vehicle):
    type_code = vehicle.model.type.code
    if type_code == "moto":
        return 1_000_000
    if vehicle.model.engine_cc >= 155:
        return 500_000
    return 300_000


def feature_list(vehicle):
    return [
        vehicle.model.transmission,
        f"{vehicle.model.helmets_count} helmets",
        f"{vehicle.model.trunk} storage",
        str(vehicle.model.year),
    ]


def spec_map(vehicle):
    return {
        "engine": f"{vehicle.model.engine_cc}cc",
        "transmission": vehicle.model.transmission,
        "fuel_consumption": f"{vehicle.model.fuel_consumption} L / 100km",
        "year": str(vehicle.model.year),
        "trunk": vehicle.model.trunk,
        "helmets_count": str(vehicle.model.helmets_count),
        "color": vehicle.color,
    }


def vehicle_gallery_payload(vehicle, request=None):
    gallery = []
    for image in vehicle.images.order_by("sort_order", "id"):
        image_url = image.image.url
        if request:
            image_url = request.build_absolute_uri(image_url)
        gallery.append({
            "id": image.id,
            "image": image_url,
            "alt_text": image.alt_text or vehicle.title,
            "is_main": image.is_main,
        })
    return gallery


def vehicle_main_image(vehicle, request=None):
    gallery = vehicle_gallery_payload(vehicle, request=request)
    if not gallery:
        return None, []
    main_image = next((image for image in gallery if image["is_main"]), gallery[0])
    return main_image["image"], gallery


def public_vehicle_payload(vehicle, lang, content, request=None):
    copy = get_vehicle_copy(vehicle.slug, lang)
    type_code = vehicle.model.type.code
    title = copy.get("title") or vehicle.title
    description = copy.get("description") or vehicle.model.description
    rental_terms = copy.get("rental_terms") or vehicle.model.rental_terms
    main_image, gallery = vehicle_main_image(vehicle, request=request)

    return {
        "id": vehicle.id,
        "name": title,
        "slug": vehicle.slug,
        "type": type_code,
        "typeLabel": content["common"]["types"].get(type_code, type_code.title()),
        "engine": f"{vehicle.model.engine_cc}cc",
        "priceUSD": float(vehicle.base_price_usd),
        "priceIDR": usd_to_idr(vehicle.base_price_usd),
        "deposit": vehicle_deposit(vehicle),
        "rating": round(vehicle.rating_avg or 0, 1),
        "reviews": vehicle.reviews_count or 0,
        "available": vehicle.status == "available",
        "accent": ACCENT_BY_SLUG.get(vehicle.slug, "#111111"),
        "features": feature_list(vehicle),
        "specs": spec_map(vehicle),
        "description": description,
        "rentalTerms": rental_terms,
        "featured": bool(vehicle.is_featured),
        "mainImage": main_image,
        "gallery": gallery,
    }


def public_addon_payload(addon):
    copy = get_addon_copy(addon.code, "en")
    meta = ADDON_META.get(addon.code, {})
    return {
        "id": addon.id,
        "code": addon.code,
        "name": copy.get("name") or addon.name,
        "description": copy.get("description") or addon.description,
        "priceUSD": float(addon.price_usd),
        "priceIDR": usd_to_idr(addon.price_usd),
        "priceType": addon.price_type,
        "icon": meta.get("icon", "➕"),
        "category": meta.get("category", "extra"),
    }


def localized_addon_payload(addon, lang):
    payload = public_addon_payload(addon)
    copy = get_addon_copy(addon.code, lang)
    payload["name"] = copy.get("name") or payload["name"]
    payload["description"] = copy.get("description") or payload["description"]
    return payload


def public_zone_payload(zone):
    return {
        "id": zone.id,
        "name": zone.name,
        "deliveryFeeUSD": float(zone.base_price_usd if not zone.is_free else Decimal("0.00")),
        "deliveryFeeIDR": usd_to_idr(zone.base_price_usd if not zone.is_free else Decimal("0.00")),
        "freeDelivery": zone.is_free,
        "timeMinutes": ZONE_MINUTES.get(zone.name, 45),
        "latitude": zone.center_lat,
        "longitude": zone.center_lng,
    }


def public_support_links():
    return [
        {
            "code": "faq",
            "title": "FAQ",
            "url": "",
            "phone": "",
        },
        {
            "code": "support_chat",
            "title": "Support Chat",
            "url": "",
            "phone": "",
        },
    ]


def localized_faq_items(lang, fallback_items):
    try:
        faq_items = list(
            FAQItem.objects.filter(is_active=True)
            .prefetch_related("translations")
            .order_by("sort_order", "id")
        )
    except (OperationalError, ProgrammingError):
        return fallback_items

    if not faq_items:
        return fallback_items

    items = []
    for faq_item in faq_items:
        translations = {translation.language.lower(): translation for translation in faq_item.translations.all()}
        translation = translations.get(lang) or translations.get(lang.split("-")[0]) or translations.get("en")
        if not translation:
            continue
        items.append({
            "id": faq_item.id,
            "q": translation.question,
            "a": translation.answer,
        })

    return items or fallback_items


class PublicSiteBootstrapView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        lang = normalize_public_language(
            request.query_params.get("lang")
            or request.headers.get("X-Language")
            or request.headers.get("Accept-Language")
        )
        content = get_public_site_content(lang)
        content["home"]["faq"]["items"] = localized_faq_items(
            lang,
            content["home"]["faq"].get("items", []),
        )

        vehicles = (
            Vehicle.objects.exclude(status="inactive")
            .select_related("model__type")
            .prefetch_related("images")
            .order_by("-is_featured", "base_price_usd", "title")
        )
        addons = Addon.objects.filter(is_active=True).order_by("sort_order", "id")
        zones = DeliveryZone.objects.filter(is_active=True).order_by("-is_free", "base_price_usd", "name")

        fleet = [public_vehicle_payload(vehicle, lang, content, request=request) for vehicle in vehicles]
        response = {
            "lang": lang,
            "languages": get_public_languages(),
            "content": content,
            "fleet": {
                "featured": [item for item in fleet if item["featured"]][:3],
                "items": fleet,
            },
            "addons": [localized_addon_payload(addon, lang) for addon in addons],
            "deliveryZones": [public_zone_payload(zone) for zone in zones],
            "deliverySlots": DEFAULT_DELIVERY_SLOTS,
            "supportLinks": public_support_links(),
        }
        return Response(response)
