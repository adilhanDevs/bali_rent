from decimal import Decimal

from django.db import migrations

ADMIN_IDR_RATE = Decimal('15650')


def backfill_base_price_idr(apps, schema_editor):
    Vehicle = apps.get_model('catalog', 'Vehicle')
    for vehicle in Vehicle.objects.filter(base_price_idr__isnull=True):
        vehicle.base_price_idr = round(vehicle.base_price_usd * ADMIN_IDR_RATE)
        vehicle.save(update_fields=['base_price_idr'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0008_vehicle_base_price_idr'),
    ]

    operations = [
        migrations.RunPython(backfill_base_price_idr, noop_reverse),
    ]
