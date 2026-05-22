from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0005_vehicletypetranslation"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicletranslation",
            name="color",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
