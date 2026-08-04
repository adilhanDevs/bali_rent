# Generated manually for admin-entered add-on IDR prices.

from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models


ADMIN_IDR_RATE = Decimal('15650')


def backfill_price_idr(apps, schema_editor):
    Addon = apps.get_model('addons', 'Addon')
    for addon in Addon.objects.all():
        if addon.price_idr is None:
            addon.price_idr = int((Decimal(addon.price_usd) * ADMIN_IDR_RATE).to_integral_value(rounding=ROUND_HALF_UP))
            addon.save(update_fields=['price_idr'])


class Migration(migrations.Migration):

    dependencies = [
        ('addons', '0003_alter_addon_price_usd'),
    ]

    operations = [
        migrations.AddField(
            model_name='addon',
            name='price_idr',
            field=models.PositiveBigIntegerField(
                blank=True,
                help_text='Exact IDR amount entered by the admin. price_usd is kept for pricing calculations.',
                null=True,
            ),
        ),
        migrations.RunPython(backfill_price_idr, migrations.RunPython.noop),
    ]
