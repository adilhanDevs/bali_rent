import math
from decimal import Decimal, ROUND_HALF_UP

from .models import DeliveryPricingRule, DeliveryZone


def haversine_distance(lat1, lon1, lat2, lon2):
    radius = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def _normalize_polygon_points(raw_points):
    if not raw_points:
        return []

    points = []
    for point in raw_points:
        if isinstance(point, dict):
            lat = point.get('lat')
            lng = point.get('lng')
        elif isinstance(point, (list, tuple)) and len(point) >= 2:
            lat, lng = point[0], point[1]
        else:
            continue

        if lat is None or lng is None:
            continue
        points.append((float(lat), float(lng)))
    return points


def point_in_polygon(lat, lng, polygon_points):
    points = _normalize_polygon_points(polygon_points)
    if len(points) < 3:
        return False

    inside = False
    x = float(lng)
    y = float(lat)
    j = len(points) - 1

    for i in range(len(points)):
        yi, xi = points[i]
        yj, xj = points[j]
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i

    return inside


def _select_zone(lat, lng):
    active_zones = DeliveryZone.objects.filter(is_active=True).prefetch_related('pricing_rules')

    nearest_fallback_zone = None
    nearest_distance = None

    for zone in active_zones:
        polygon = zone.polygon or zone.polygon_json
        if polygon and point_in_polygon(lat, lng, polygon):
            return zone, Decimal('0.00')

        if zone.center_lat is not None and zone.center_lng is not None:
            distance = Decimal(str(haversine_distance(lat, lng, zone.center_lat, zone.center_lng)))
            if distance <= Decimal(str(zone.radius_km)):
                return zone, distance
            if nearest_distance is None or distance < nearest_distance:
                nearest_distance = distance
                nearest_fallback_zone = zone

    return None, nearest_distance or Decimal('0.00')


def _get_zone_price(zone, distance_km=Decimal('0.00')):
    if zone.is_free or zone.free_delivery:
        return Decimal('0.00')

    rule = zone.pricing_rules.filter(is_active=True).order_by('-created_at').first()
    if rule:
        return rule.price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if zone.base_price_usd or zone.price_per_km_usd:
        return (
            Decimal(zone.base_price_usd) + (Decimal(zone.price_per_km_usd) * Decimal(str(distance_km)))
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return Decimal('25.00')


def calculate_delivery_price(lat, lng):
    lat = float(lat)
    lng = float(lng)
    zone, distance_km = _select_zone(lat, lng)

    if zone:
        price = _get_zone_price(zone, distance_km)
        return {
            'is_free': price == Decimal('0.00'),
            'price': price,
            'currency': 'USD',
            'zone': zone,
            'distance_km': Decimal(str(distance_km)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'is_within_zone': True,
        }

    return {
        'is_free': False,
        'price': Decimal('25.00'),
        'currency': 'USD',
        'zone': None,
        'distance_km': Decimal(str(distance_km)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'is_within_zone': False,
        'message': 'Outside standard delivery zones',
    }
