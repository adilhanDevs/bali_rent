from django.db import migrations, models


def preserve_current_catalog_order(apps, schema_editor):
    Vehicle = apps.get_model('catalog', 'Vehicle')
    vehicle_ids = list(Vehicle.objects.order_by('-created_at', '-id').values_list('id', flat=True))
    for position, vehicle_id in enumerate(vehicle_ids, start=1):
        Vehicle.objects.filter(pk=vehicle_id).update(sort_order=position)


class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0010_vehicle_quantity'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicle',
            name='sort_order',
            field=models.PositiveIntegerField(
                db_index=True,
                default=0,
                help_text='Manual order in the public catalog. Lower numbers are shown first.',
            ),
        ),
        migrations.RunPython(preserve_current_catalog_order, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name='vehicle',
            options={'ordering': ['sort_order', 'id']},
        ),
    ]
