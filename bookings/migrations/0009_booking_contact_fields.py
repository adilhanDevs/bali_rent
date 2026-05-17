from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0008_booking_bookings_bo_user_id_5943d6_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='contact_has_telegram',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='booking',
            name='contact_has_wechat',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='booking',
            name='contact_has_whatsapp',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='booking',
            name='contact_name',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='booking',
            name='contact_phone',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
    ]
