import math
from decimal import Decimal
from .models import DeliveryZone

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_delivery_price(lat, lng):
    active_zones = DeliveryZone.objects.filter(is_active=True)
    
    best_zone = None
    min_distance = float('inf')
    
    for zone in active_zones:
        distance = haversine_distance(lat, lng, zone.center_lat, zone.center_lng)
        if distance <= zone.radius_km:
            if best_zone is None or distance < min_distance:
                best_zone = zone
                min_distance = distance
                
    if best_zone:
        if best_zone.free_delivery:
            return {
                "is_free": True,
                "price": Decimal("0.00"),
                "currency": "USD",
                "zone": best_zone
            }
        else:
            # Paid zone calculation: base + price_per_km
            price = best_zone.base_price_usd + (best_zone.price_per_km_usd * Decimal(str(min_distance)))
            return {
                "is_free": False,
                "price": price.quantize(Decimal("0.01")),
                "currency": "USD",
                "zone": best_zone
            }
            
    # Outside all zones - default high price or handled as "too far"
    # For Phase 1, let's return a default "outside" response
    return {
        "is_free": False,
        "price": Decimal("25.00"), # Default flat fee for far delivery
        "currency": "USD",
        "zone": None,
        "message": "Outside standard delivery zones"
    }
