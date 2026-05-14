from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0006_merge_20260501_1106'),
    ]

    operations = [
        migrations.CreateModel(
            name='LocationSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(
                    choices=[
                        ('en', 'English'),
                        ('ru', 'Русский'),
                        ('zh', '中文'),
                        ('id', 'Indonesia'),
                        ('de', 'Deutsch'),
                        ('fr', 'Français'),
                    ],
                    max_length=10,
                    unique=True,
                )),
                ('title1', models.CharField(blank=True, help_text='First line of section heading', max_length=200)),
                ('title2', models.CharField(blank=True, help_text='Second line (highlighted in yellow)', max_length=200)),
                ('description', models.TextField(blank=True, help_text='Paragraph under the heading')),
                ('map_eyebrow', models.CharField(blank=True, help_text='Small label above map region name', max_length=200)),
                ('map_region', models.CharField(blank=True, help_text='Region name on the map overlay', max_length=200)),
                ('is_active', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Location Section Content',
                'verbose_name_plural': 'Location Section Content',
                'ordering': ['language'],
            },
        ),
        migrations.CreateModel(
            name='DeliveryZoneTranslation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(max_length=10)),
                ('name', models.CharField(max_length=100)),
                ('zone', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='translations',
                    to='delivery.deliveryzone',
                )),
            ],
            options={
                'ordering': ['zone', 'language'],
                'unique_together': {('zone', 'language')},
            },
        ),
    ]
