from decimal import Decimal
from pathlib import Path
import shutil
import os
import sys
import django


MEDIA_ROOT = Path("media")
PHOTO_SOURCE_DIR = Path("photo_for_scooters")
MOCK_SCOOTER_PHOTOS = {
    "vehicles/scooter-photo-1.png": PHOTO_SOURCE_DIR / "image.png",
    "vehicles/scooter-photo-2.png": PHOTO_SOURCE_DIR / "image copy.png",
    "vehicles/scooter-photo-3.png": PHOTO_SOURCE_DIR / "image copy 2.png",
}

VEHICLES = [
    {
        "brand": "Honda",
        "name": "PCX 160",
        "type_code": "scooter",
        "type_name": "Scooter",
        "engine_cc": 160,
        "transmission": "Automatic",
        "fuel_consumption": 2.1,
        "year": 2024,
        "trunk": "30L",
        "helmets_count": 2,
        "description": "Premium city scooter with smooth comfort for Bali transfers and daily rides.",
        "rental_terms": "Helmet included. Minimum age 18. International driving permit recommended.",
        "title": "Honda PCX 160",
        "slug": "honda-pcx-160",
        "sku": "PCX-160-001",
        "color": "Matte Black",
        "base_price_usd": Decimal("5.50"),
        "status": "available",
        "mileage": 4200,
        "rating_avg": 4.9,
        "reviews_count": 124,
        "is_featured": True,
        "image": "vehicles/scooter-photo-1.png",
    },
    {
        "brand": "Yamaha",
        "name": "NMAX 155",
        "type_code": "maxi",
        "type_name": "Maxi Scooter",
        "engine_cc": 155,
        "transmission": "Automatic",
        "fuel_consumption": 2.0,
        "year": 2024,
        "trunk": "25L",
        "helmets_count": 2,
        "description": "Comfortable maxi scooter for longer Bali routes and daily rentals.",
        "rental_terms": "Helmet included. Minimum age 18. International driving permit recommended.",
        "title": "Yamaha NMAX 155",
        "slug": "yamaha-nmax-155",
        "sku": "NMAX-155-001",
        "color": "Midnight Blue",
        "base_price_usd": Decimal("6.20"),
        "status": "available",
        "mileage": 3100,
        "rating_avg": 4.8,
        "reviews_count": 98,
        "is_featured": True,
        "image": "vehicles/scooter-photo-2.png",
    },
    {
        "brand": "Honda",
        "name": "ADV 160",
        "type_code": "maxi",
        "type_name": "Maxi Scooter",
        "engine_cc": 160,
        "transmission": "Automatic",
        "fuel_consumption": 2.3,
        "year": 2024,
        "trunk": "28L",
        "helmets_count": 2,
        "description": "Adventure-style scooter that handles mixed Bali roads with ease.",
        "rental_terms": "Helmet included. Minimum age 18. International driving permit recommended.",
        "title": "Honda ADV 160",
        "slug": "honda-adv-160",
        "sku": "ADV-160-001",
        "color": "Graphite Black",
        "base_price_usd": Decimal("7.10"),
        "status": "available",
        "mileage": 2900,
        "rating_avg": 4.9,
        "reviews_count": 67,
        "is_featured": True,
        "image": "vehicles/scooter-photo-3.png",
    },
    {
        "brand": "Yamaha",
        "name": "Aerox 155",
        "type_code": "scooter",
        "type_name": "Scooter",
        "engine_cc": 155,
        "transmission": "Automatic",
        "fuel_consumption": 1.9,
        "year": 2024,
        "trunk": "24L",
        "helmets_count": 2,
        "description": "Sporty scooter with quick acceleration for city rides.",
        "rental_terms": "Helmet included. Minimum age 18. International driving permit recommended.",
        "title": "Yamaha Aerox 155",
        "slug": "yamaha-aerox-155",
        "sku": "AEROX-155-001",
        "color": "Onyx",
        "base_price_usd": Decimal("5.20"),
        "status": "available",
        "mileage": 5100,
        "rating_avg": 4.7,
        "reviews_count": 112,
        "is_featured": False,
        "image": "vehicles/scooter-photo-1.png",
    },
    {
        "brand": "Honda",
        "name": "Vario 160",
        "type_code": "scooter",
        "type_name": "Scooter",
        "engine_cc": 160,
        "transmission": "Automatic",
        "fuel_consumption": 2.0,
        "year": 2024,
        "trunk": "18L",
        "helmets_count": 2,
        "description": "Reliable everyday scooter with balanced handling and low fuel use.",
        "rental_terms": "Helmet included. Minimum age 18. International driving permit recommended.",
        "title": "Honda Vario 160",
        "slug": "honda-vario-160",
        "sku": "VARIO-160-001",
        "color": "Deep Plum",
        "base_price_usd": Decimal("4.50"),
        "status": "rented",
        "mileage": 3900,
        "rating_avg": 4.6,
        "reviews_count": 89,
        "is_featured": False,
        "image": "vehicles/scooter-photo-2.png",
    },
    {
        "brand": "Royal Enfield",
        "name": "Meteor 350",
        "type_code": "moto",
        "type_name": "Motorcycle",
        "engine_cc": 350,
        "transmission": "Manual",
        "fuel_consumption": 3.5,
        "year": 2023,
        "trunk": "Touring Ready",
        "helmets_count": 1,
        "description": "Classic motorcycle for scenic coastal trips and longer rides.",
        "rental_terms": "Experienced riders only. Helmet included. International driving permit recommended.",
        "title": "Royal Enfield Meteor 350",
        "slug": "royal-enfield-meteor",
        "sku": "METEOR-350-001",
        "color": "Fireball Red",
        "base_price_usd": Decimal("12.70"),
        "status": "available",
        "mileage": 1800,
        "rating_avg": 5.0,
        "reviews_count": 43,
        "is_featured": True,
        "image": "vehicles/scooter-photo-3.png",
    },
    {
        "brand": "Honda",
        "name": "Scoopy 110",
        "type_code": "scooter",
        "type_name": "Scooter",
        "engine_cc": 110,
        "transmission": "Automatic",
        "fuel_consumption": 1.8,
        "year": 2024,
        "trunk": "15L",
        "helmets_count": 1,
        "description": "Compact retro scooter that is easy to ride and park around Bali.",
        "rental_terms": "Helmet included. Minimum age 18. International driving permit recommended.",
        "title": "Honda Scoopy 110",
        "slug": "honda-scoopy-110",
        "sku": "SCOOPY-110-001",
        "color": "Cream White",
        "base_price_usd": Decimal("4.20"),
        "status": "available",
        "mileage": 2600,
        "rating_avg": 4.7,
        "reviews_count": 74,
        "is_featured": False,
        "image": "vehicles/scooter-photo-1.png",
    },
    {
        "brand": "Yamaha",
        "name": "Fazzio Neo 125",
        "type_code": "scooter",
        "type_name": "Scooter",
        "engine_cc": 125,
        "transmission": "Automatic",
        "fuel_consumption": 1.7,
        "year": 2024,
        "trunk": "17L",
        "helmets_count": 1,
        "description": "Stylish lightweight scooter with modern features for short stays.",
        "rental_terms": "Helmet included. Minimum age 18. International driving permit recommended.",
        "title": "Yamaha Fazzio Neo 125",
        "slug": "yamaha-fazzio-125",
        "sku": "FAZZIO-125-001",
        "color": "Mint Green",
        "base_price_usd": Decimal("4.40"),
        "status": "available",
        "mileage": 2100,
        "rating_avg": 4.8,
        "reviews_count": 58,
        "is_featured": False,
        "image": "vehicles/scooter-photo-2.png",
    },
    {
        "brand": "Yamaha",
        "name": "XMAX 300",
        "type_code": "maxi",
        "type_name": "Maxi Scooter",
        "engine_cc": 300,
        "transmission": "Automatic",
        "fuel_consumption": 3.0,
        "year": 2024,
        "trunk": "44L",
        "helmets_count": 2,
        "description": "Touring-ready maxi scooter for premium island travel.",
        "rental_terms": "Helmet included. Minimum age 21. International driving permit recommended.",
        "title": "Yamaha XMAX 300",
        "slug": "yamaha-xmax-300",
        "sku": "XMAX-300-001",
        "color": "Tech Kamo",
        "base_price_usd": Decimal("11.20"),
        "status": "available",
        "mileage": 1500,
        "rating_avg": 4.9,
        "reviews_count": 31,
        "is_featured": True,
        "image": "vehicles/scooter-photo-3.png",
    },
    {
        "brand": "Vespa",
        "name": "Primavera 125",
        "type_code": "scooter",
        "type_name": "Scooter",
        "engine_cc": 125,
        "transmission": "Automatic",
        "fuel_consumption": 2.1,
        "year": 2024,
        "trunk": "16L",
        "helmets_count": 1,
        "description": "Iconic Italian scooter for stylish rides around Seminyak and Canggu.",
        "rental_terms": "Helmet included. Minimum age 18. International driving permit recommended.",
        "title": "Vespa Primavera 125",
        "slug": "vespa-primavera-125",
        "sku": "VESPA-125-001",
        "color": "Pastel Blue",
        "base_price_usd": Decimal("8.40"),
        "status": "available",
        "mileage": 2400,
        "rating_avg": 4.8,
        "reviews_count": 52,
        "is_featured": True,
        "image": "vehicles/scooter-photo-1.png",
    },
]

ADDONS = [
    ("helmet_full", "Full-Face Helmet", "Premium full-face helmet.", Decimal("1.00"), "per_day", 1),
    ("insurance", "Full Insurance", "Complete protection against accidents.", Decimal("1.60"), "per_day", 2),
    ("gps", "GPS Navigator", "Offline Bali maps loaded.", Decimal("1.30"), "per_day", 3),
    ("raincoat", "Rain Poncho", "Lightweight waterproof cover.", Decimal("0.60"), "per_day", 4),
    ("phone_mount", "Phone Mount", "Universal secure mount.", Decimal("0.60"), "per_day", 5),
    ("wifi", "Pocket WiFi 4G", "Unlimited data in Bali.", Decimal("2.30"), "per_day", 6),
]

DELIVERY_ZONES = [
    ("Seminyak", -8.6900, 115.1680, True, Decimal("0.00"), Decimal("0.50"), 7.0),
    ("Canggu", -8.6480, 115.1380, True, Decimal("0.00"), Decimal("0.50"), 7.0),
    ("Kuta", -8.7220, 115.1720, True, Decimal("0.00"), Decimal("0.50"), 6.0),
    ("Ubud", -8.5069, 115.2625, False, Decimal("3.20"), Decimal("0.60"), 10.0),
]

ADDON_TRANSLATIONS = {
    "helmet_full": {
        "ru": {"name": "Полнолицевой шлем", "description": "Премиум-класс полнолицевой шлем."},
        "zh": {"name": "全覆盖头盔", "description": "高级全覆盖头盔。"},
        "id": {"name": "Helm Full-Face", "description": "Helm full-face premium."},
        "de": {"name": "Vollschutzhelm", "description": "Premium-Vollschutzhelm."},
        "fr": {"name": "Casque intégral", "description": "Casque integral premium."},
    },
    "insurance": {
        "ru": {"name": "Полная страховка", "description": "Полная защита от несчастных случаев."},
        "zh": {"name": "完整保险", "description": "事故完全保护。"},
        "id": {"name": "Asuransi Penuh", "description": "Perlindungan lengkap terhadap kecelakaan."},
        "de": {"name": "Vollversicherung", "description": "Vollständiger Schutz vor Unfällen."},
        "fr": {"name": "Assurance Complète", "description": "Protection complète contre les accidents."},
    },
    "gps": {
        "ru": {"name": "GPS Навигатор", "description": "Офлайн карты Бали загружены."},
        "zh": {"name": "GPS导航仪", "description": "离线巴厘岛地图已加载。"},
        "id": {"name": "Navigator GPS", "description": "Peta Bali offline dimuat."},
        "de": {"name": "GPS-Navigator", "description": "Offline-Karten von Bali geladen."},
        "fr": {"name": "Navigateur GPS", "description": "Cartes hors ligne de Bali chargées."},
    },
    "raincoat": {
        "ru": {"name": "Дождевой плащ", "description": "Легкий водонепроницаемый плащ."},
        "zh": {"name": "雨衣", "description": "轻量级防水罩。"},
        "id": {"name": "Ponco Hujan", "description": "Penutup tahan air yang ringan."},
        "de": {"name": "Regencape", "description": "Leichte wasserdichte Abdeckung."},
        "fr": {"name": "Cape Pluie", "description": "Couverture imperméable légère."},
    },
    "phone_mount": {
        "ru": {"name": "Крепление для телефона", "description": "Универсальное безопасное крепление."},
        "zh": {"name": "手机支架", "description": "通用安全安装。"},
        "id": {"name": "Penyangga Ponsel", "description": "Dudukan universal yang aman."},
        "de": {"name": "Telefonhalter", "description": "Universelle sichere Halterung."},
        "fr": {"name": "Support Téléphone", "description": "Montage sécurisé universel."},
    },
    "wifi": {
        "ru": {"name": "Карманный WiFi 4G", "description": "Неограниченные данные на Бали."},
        "zh": {"name": "口袋WiFi 4G", "description": "巴厘岛无限数据。"},
        "id": {"name": "Pocket WiFi 4G", "description": "Data unlimited di Bali."},
        "de": {"name": "Pocket WiFi 4G", "description": "Unbegrenzte Daten in Bali."},
        "fr": {"name": "Pocket WiFi 4G", "description": "Données illimitées à Bali."},
    },
}


def sync_mock_vehicle_photos():
    vehicles_dir = MEDIA_ROOT / "vehicles"
    vehicles_dir.mkdir(parents=True, exist_ok=True)

    for target, source in MOCK_SCOOTER_PHOTOS.items():
        if not source.exists():
            continue
        shutil.copy2(source, MEDIA_ROOT / target)


def create_mock_data():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bali_rent.settings")
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    django.setup()

    from addons.models import Addon, AddonTranslation
    from catalog.models import Vehicle, VehicleImage, VehicleModel, VehicleType
    from delivery.models import DeliveryZone

    sync_mock_vehicle_photos()

    for item in VEHICLES:
        vehicle_type, _ = VehicleType.objects.get_or_create(
            code=item["type_code"],
            defaults={"name": item["type_name"]},
        )
        if vehicle_type.name != item["type_name"]:
            vehicle_type.name = item["type_name"]
            vehicle_type.save(update_fields=["name"])

        model, _ = VehicleModel.objects.update_or_create(
            brand=item["brand"],
            name=item["name"],
            year=item["year"],
            defaults={
                "type": vehicle_type,
                "engine_cc": item["engine_cc"],
                "transmission": item["transmission"],
                "fuel_consumption": item["fuel_consumption"],
                "trunk": item["trunk"],
                "helmets_count": item["helmets_count"],
                "description": item["description"],
                "rental_terms": item["rental_terms"],
            },
        )

        vehicle, _ = Vehicle.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "model": model,
                "title": item["title"],
                "sku": item["sku"],
                "color": item["color"],
                "base_price_usd": item["base_price_usd"],
                "status": item["status"],
                "mileage": item["mileage"],
                "rating_avg": item["rating_avg"],
                "reviews_count": item["reviews_count"],
                "is_featured": item["is_featured"],
            },
        )

        image_path = MEDIA_ROOT / item["image"]
        if image_path.exists():
            vehicle.images.exclude(image=item["image"]).delete()
            VehicleImage.objects.update_or_create(
                vehicle=vehicle,
                image=item["image"],
                defaults={
                    "alt_text": item["title"],
                    "sort_order": 0,
                    "is_main": True,
                },
            )

    for code, name, description, price_usd, price_type, sort_order in ADDONS:
        Addon.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "description": description,
                "price_usd": price_usd,
                "price_type": price_type,
                "is_active": True,
                "sort_order": sort_order,
            },
        )

    for addon_code, translations_by_lang in ADDON_TRANSLATIONS.items():
        addon = Addon.objects.filter(code=addon_code).first()
        if not addon:
            continue
        for lang, trans_data in translations_by_lang.items():
            AddonTranslation.objects.update_or_create(
                addon=addon,
                language=lang,
                defaults={
                    "name": trans_data["name"],
                    "description": trans_data["description"],
                },
            )

    for name, center_lat, center_lng, is_free, base_price_usd, price_per_km_usd, radius_km in DELIVERY_ZONES:
        DeliveryZone.objects.update_or_create(
            name=name,
            defaults={
                "center_lat": center_lat,
                "center_lng": center_lng,
                "radius_km": radius_km,
                "is_free": is_free,
                "base_price_usd": base_price_usd,
                "price_per_km_usd": price_per_km_usd,
                "is_active": True,
            },
        )

    print(f"Mock data created successfully: {len(VEHICLES)} vehicles with local images.")


if __name__ == "__main__":
    create_mock_data()
