from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('addons', '0003_alter_addon_price_usd'),
        ('bookings', '0009_booking_contact_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookingaddon',
            name='addon',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='addons.addon'),
        ),
    ]
