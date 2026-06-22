from decimal import Decimal

from django.db import migrations

ADMIN_IDR_RATE = Decimal('15650')


def backfill_price_idr(apps, schema_editor):
    ScooterRentalRate = apps.get_model('pricing', 'ScooterRentalRate')
    for rate in ScooterRentalRate.objects.filter(price_idr__isnull=True):
        rate.price_idr = round(rate.price_usd * ADMIN_IDR_RATE)
        rate.save(update_fields=['price_idr'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0007_scooterrentalrate_price_idr'),
    ]

    operations = [
        migrations.RunPython(backfill_price_idr, noop_reverse),
    ]
