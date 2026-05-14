from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0003_alter_vehicle_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicletranslation',
            name='transmission',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='vehicletranslation',
            name='trunk',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
