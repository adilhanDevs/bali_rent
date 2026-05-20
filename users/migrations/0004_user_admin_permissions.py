from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_alter_user_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='admin_permissions',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
