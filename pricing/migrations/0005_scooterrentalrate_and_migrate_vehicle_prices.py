# Generated manually for flexible scooter rental rates.

import decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


DEFAULT_TIER_BREAKS = (
    (1, 1),
    (2, 6),
    (7, 15),
    (16, 29),
    (30, None),
)


def seed_default_rental_rates(apps, schema_editor):
    Vehicle = apps.get_model('catalog', 'Vehicle')
    ScooterRentalRate = apps.get_model('pricing', 'ScooterRentalRate')

    existing_vehicle_ids = set(
        ScooterRentalRate.objects.values_list('scooter_id', flat=True)
    )
    rows_to_create = []

    for vehicle in Vehicle.objects.all().iterator():
        if vehicle.id in existing_vehicle_ids:
            continue
        for min_days, max_days in DEFAULT_TIER_BREAKS:
            rows_to_create.append(
                ScooterRentalRate(
                    scooter_id=vehicle.id,
                    min_days=min_days,
                    max_days=max_days,
                    price_usd=vehicle.base_price_usd,
                    billing_period_days=1,
                )
            )

    if rows_to_create:
        ScooterRentalRate.objects.bulk_create(rows_to_create)


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0006_vehicletranslation_color'),
        ('pricing', '0004_cleanup_orphaned_price_log_users'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScooterRentalRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('min_days', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('max_days', models.PositiveIntegerField(blank=True, help_text='Leave empty for an open-ended range.', null=True, validators=[django.core.validators.MinValueValidator(1)])),
                ('price_usd', models.DecimalField(decimal_places=2, help_text='Price charged for each billing period.', max_digits=10, validators=[django.core.validators.MinValueValidator(decimal.Decimal('0.00'))])),
                ('billing_period_days', models.PositiveIntegerField(default=1, help_text='1 for per-day pricing, 30 for monthly pricing, etc.', validators=[django.core.validators.MinValueValidator(1)])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('scooter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rental_rates', to='catalog.vehicle')),
            ],
            options={
                'ordering': ['min_days', 'max_days', 'id'],
                'indexes': [
                    models.Index(fields=['scooter', 'min_days'], name='pricing_sco_scooter_b26abf_idx'),
                    models.Index(fields=['scooter', 'max_days'], name='pricing_sco_scooter_9576bf_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(fields=('scooter', 'min_days', 'max_days', 'billing_period_days'), name='unique_scooter_rental_rate_range'),
                ],
            },
        ),
        migrations.RunPython(seed_default_rental_rates, migrations.RunPython.noop),
    ]
