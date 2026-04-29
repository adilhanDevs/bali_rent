from decimal import Decimal

import django.core.validators
from django.db import migrations, models
from django.utils.text import slugify


def forwards_refactor_pricing(apps, schema_editor):
    Season = apps.get_model('pricing', 'Season')
    DevicePricingRule = apps.get_model('pricing', 'DevicePricingRule')
    GeoPricingRule = apps.get_model('pricing', 'GeoPricingRule')
    PriceCalculationLog = apps.get_model('pricing', 'PriceCalculationLog')

    seen_codes = set()
    for season in Season.objects.all().order_by('pk'):
        base_code = slugify(season.name) or f'season-{season.pk}'
        code = base_code
        counter = 1
        while code in seen_codes or Season.objects.exclude(pk=season.pk).filter(code=code).exists():
            code = f'{base_code}-{counter}'
            counter += 1
        season.code = code
        seen_codes.add(code)
        if not season.multiplier:
            season.multiplier = Decimal('1.00')
        season.save(update_fields=['code', 'multiplier'])

    for rule in DevicePricingRule.objects.all():
        adjustment = rule.adjustment_percent or Decimal('0.00')
        rule.multiplier = (Decimal('1.00') + (adjustment / Decimal('100'))).quantize(Decimal('0.01'))
        rule.save(update_fields=['multiplier'])

    for rule in GeoPricingRule.objects.all():
        adjustment = rule.adjustment_percent or Decimal('0.00')
        rule.multiplier = (Decimal('1.00') + (adjustment / Decimal('100'))).quantize(Decimal('0.01'))
        rule.save(update_fields=['multiplier'])

    for log in PriceCalculationLog.objects.all():
        payload = log.payload_json or {}
        base_price = log.final_price
        if isinstance(payload, dict):
            breakdown = payload.get('breakdown') or {}
            if 'base_price' in breakdown:
                base_price = Decimal(str(breakdown['base_price']))
            else:
                steps = payload.get('steps') or []
                if steps:
                    first_step = steps[0] or {}
                    if 'subtotal' in first_step:
                        base_price = Decimal(str(first_step['subtotal']))
        log.base_price = base_price.quantize(Decimal('0.01'))
        log.save(update_fields=['base_price'])


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='PricingRule',
        ),
        migrations.AlterModelOptions(
            name='season',
            options={'ordering': ['start_date', 'name']},
        ),
        migrations.AlterModelOptions(
            name='scooterseasonprice',
            options={'ordering': ['season__start_date', 'scooter__title']},
        ),
        migrations.AlterModelOptions(
            name='occupancypricingrule',
            options={'ordering': ['threshold_percent']},
        ),
        migrations.AlterModelOptions(
            name='devicepricingrule',
            options={'ordering': ['device_type', 'country_code']},
        ),
        migrations.AlterModelOptions(
            name='geopricingrule',
            options={'ordering': ['country_code', 'city']},
        ),
        migrations.AlterModelOptions(
            name='pricecalculationlog',
            options={'ordering': ['-created_at']},
        ),
        migrations.AddField(
            model_name='season',
            name='code',
            field=models.SlugField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='season',
            name='multiplier',
            field=models.DecimalField(decimal_places=2, default=Decimal('1.00'), max_digits=6, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]),
        ),
        migrations.RenameField(
            model_name='scooterseasonprice',
            old_name='price_per_day',
            new_name='price_per_day_usd',
        ),
        migrations.AddField(
            model_name='occupancypricingrule',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.RenameField(
            model_name='occupancypricingrule',
            old_name='min_occupancy_percent',
            new_name='threshold_percent',
        ),
        migrations.RenameField(
            model_name='occupancypricingrule',
            old_name='adjustment_percent',
            new_name='price_increase_percent',
        ),
        migrations.RenameField(
            model_name='devicepricingrule',
            old_name='platform',
            new_name='device_type',
        ),
        migrations.AddField(
            model_name='devicepricingrule',
            name='country_code',
            field=models.CharField(blank=True, help_text='Optional ISO 3166-1 alpha-2', max_length=2, null=True),
        ),
        migrations.AddField(
            model_name='devicepricingrule',
            name='multiplier',
            field=models.DecimalField(decimal_places=2, default=Decimal('1.00'), max_digits=6, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]),
        ),
        migrations.AddField(
            model_name='devicepricingrule',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddField(
            model_name='geopricingrule',
            name='city',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='geopricingrule',
            name='multiplier',
            field=models.DecimalField(decimal_places=2, default=Decimal('1.00'), max_digits=6, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]),
        ),
        migrations.AddField(
            model_name='geopricingrule',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.RenameField(
            model_name='pricecalculationlog',
            old_name='calculation_snapshot',
            new_name='payload_json',
        ),
        migrations.RenameField(
            model_name='pricecalculationlog',
            old_name='total_price',
            new_name='final_price',
        ),
        migrations.AddField(
            model_name='pricecalculationlog',
            name='base_price',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10),
            preserve_default=False,
        ),
        migrations.RunPython(forwards_refactor_pricing, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='season',
            name='code',
            field=models.SlugField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='scooterseasonprice',
            name='price_per_day_usd',
            field=models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))]),
        ),
        migrations.AlterField(
            model_name='occupancypricingrule',
            name='threshold_percent',
            field=models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)]),
        ),
        migrations.AlterField(
            model_name='occupancypricingrule',
            name='price_increase_percent',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=6),
        ),
        migrations.AlterField(
            model_name='devicepricingrule',
            name='device_type',
            field=models.CharField(choices=[('ios', 'iOS'), ('android', 'Android'), ('web', 'Web')], max_length=20),
        ),
        migrations.AlterField(
            model_name='geopricingrule',
            name='country_code',
            field=models.CharField(help_text='ISO 3166-1 alpha-2', max_length=2),
        ),
        migrations.AlterUniqueTogether(
            name='scooterseasonprice',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='occupancypricingrule',
            name='name',
        ),
        migrations.RemoveField(
            model_name='occupancypricingrule',
            name='max_occupancy_percent',
        ),
        migrations.RemoveField(
            model_name='devicepricingrule',
            name='name',
        ),
        migrations.RemoveField(
            model_name='devicepricingrule',
            name='adjustment_percent',
        ),
        migrations.RemoveField(
            model_name='geopricingrule',
            name='name',
        ),
        migrations.RemoveField(
            model_name='geopricingrule',
            name='adjustment_percent',
        ),
        migrations.AddConstraint(
            model_name='scooterseasonprice',
            constraint=models.UniqueConstraint(fields=('scooter', 'season'), name='unique_scooter_season_price'),
        ),
        migrations.AddConstraint(
            model_name='occupancypricingrule',
            constraint=models.UniqueConstraint(fields=('threshold_percent',), name='unique_occupancy_threshold'),
        ),
        migrations.AddConstraint(
            model_name='devicepricingrule',
            constraint=models.UniqueConstraint(fields=('device_type', 'country_code'), name='unique_device_country_pricing_rule'),
        ),
        migrations.AddConstraint(
            model_name='geopricingrule',
            constraint=models.UniqueConstraint(fields=('country_code', 'city'), name='unique_geo_pricing_rule'),
        ),
        migrations.AddIndex(
            model_name='season',
            index=models.Index(fields=['code'], name='pricing_sea_code_16da58_idx'),
        ),
    ]
