from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0007_deliveryzonetranslation_locationsection'),
    ]

    operations = [
        migrations.AddField(
            model_name='locationsection',
            name='zones_label',
            field=models.CharField(blank=True, help_text='Eyebrow above zones grid, e.g. "01 / 02 · ZONES"', max_length=200),
        ),
        migrations.AddField(
            model_name='locationsection',
            name='zones_title',
            field=models.CharField(blank=True, help_text='Heading above zones grid, e.g. "Our delivery zones."', max_length=200),
        ),
        migrations.AddField(
            model_name='locationsection',
            name='zones_desc',
            field=models.TextField(blank=True, help_text='Description paragraph above zones grid'),
        ),
    ]
