from users.models import User
from catalog.models import VehicleType, VehicleModel, Vehicle
from addons.models import Addon
from delivery.models import DeliveryZone
from django.utils.text import slugify
from decimal import Decimal

# 1. Vehicle Type
scooter_type, _ = VehicleType.objects.get_or_create(code='scooter', name='Scooter')

# 2. Vehicle Model
vario_model, _ = VehicleModel.objects.get_or_create(
    name='Vario 160',
    brand='Honda',
    type=scooter_type,
    engine_cc=160,
    transmission='Automatic',
    fuel_consumption=2.1,
    year=2024,
    trunk='18L',
    helmets_count=2,
    description='Powerful and modern scooter for Bali roads.',
    rental_terms='Valid license required. Minimum age 18.'
)

# 3. Vehicle
vehicle, _ = Vehicle.objects.get_or_create(
    model=vario_model,
    sku='VAR-001',
    defaults={
        'title': 'Honda Vario 160 Black Edition',
        'slug': 'honda-vario-160-black',
        'color': 'Matte Black',
        'base_price_usd': Decimal('15.00'),
        'status': 'available',
        'is_featured': True
    }
)

# 4. Addons
Addon.objects.get_or_create(
    code='helmet_extra',
    defaults={
        'name': 'Extra Helmet',
        'description': 'Additional high-quality helmet.',
        'price_usd': Decimal('2.00'),
        'price_type': 'per_day'
    }
)
Addon.objects.get_or_create(
    code='insurance_full',
    defaults={
        'name': 'Full Insurance',
        'description': 'Complete protection against accidents.',
        'price_usd': Decimal('5.00'),
        'price_type': 'per_day'
    }
)

# 5. Delivery Zone
DeliveryZone.objects.get_or_create(
    name='Canggu/Seminyak',
    defaults={
        'center_lat': -8.6478,
        'center_lng': 115.1385,
        'free_delivery': True,
        'base_price_usd': Decimal('0.00'),
        'price_per_km_usd': Decimal('0.50'),
        'is_active': True
    }
)

print("Mock data created successfully!")
