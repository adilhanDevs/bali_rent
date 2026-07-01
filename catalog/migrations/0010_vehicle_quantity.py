from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0009_backfill_base_price_idr'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicle',
            name='quantity',
            field=models.PositiveIntegerField(default=1, help_text='Number of identical physical units this card represents. The card stays bookable until this many bookings overlap the requested dates, so several identical scooters can share one catalog card instead of duplicating it.'),
        ),
    ]
