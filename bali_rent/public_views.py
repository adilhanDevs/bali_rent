from decimal import Decimal

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from addons.models import Addon
from catalog.models import Vehicle
from delivery.models import DeliveryZone

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


def public_vehicle_payload(vehicle, lang, content):
    copy = get_vehicle_copy(vehicle.slug, lang)
    type_code = vehicle.model.type.code
    title = copy.get("title") or vehicle.title
    description = copy.get("description") or vehicle.model.description
    rental_terms = copy.get("rental_terms") or vehicle.model.rental_terms

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
        "deliveryFeeUSD": float(zone.base_price_usd if not zone.free_delivery else Decimal("0.00")),
        "deliveryFeeIDR": usd_to_idr(zone.base_price_usd if not zone.free_delivery else Decimal("0.00")),
        "freeDelivery": zone.free_delivery,
        "timeMinutes": ZONE_MINUTES.get(zone.name, 45),
        "latitude": zone.center_lat,
        "longitude": zone.center_lng,
    }


class PublicSiteBootstrapView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        lang = normalize_public_language(
            request.query_params.get("lang")
            or request.headers.get("X-Language")
            or request.headers.get("Accept-Language")
        )
        content = get_public_site_content(lang)

        vehicles = (
            Vehicle.objects.exclude(status="inactive")
            .select_related("model__type")
            .order_by("-is_featured", "base_price_usd", "title")
        )
        addons = Addon.objects.filter(is_active=True).order_by("sort_order", "id")
        zones = DeliveryZone.objects.filter(is_active=True).order_by("-free_delivery", "base_price_usd", "name")

        fleet = [public_vehicle_payload(vehicle, lang, content) for vehicle in vehicles]
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
        }
        return Response(response)
