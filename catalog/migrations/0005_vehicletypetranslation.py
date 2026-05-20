from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_vehicletranslation_transmission_trunk"),
    ]

    operations = [
        migrations.CreateModel(
            name="VehicleTypeTranslation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("language", models.CharField(max_length=10)),
                ("name", models.CharField(max_length=100)),
                ("vehicle_type", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="translations", to="catalog.vehicletype")),
            ],
            options={
                "unique_together": {("vehicle_type", "language")},
            },
        ),
    ]
