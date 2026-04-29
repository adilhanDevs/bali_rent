from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils.text import slugify


def populate_campaign_codes(apps, schema_editor):
    PromotionCampaign = apps.get_model('marketing', 'PromotionCampaign')
    seen_codes = set()

    for campaign in PromotionCampaign.objects.all().order_by('pk'):
        base_code = slugify(campaign.name) or f'campaign-{campaign.pk}'
        code = base_code
        counter = 1
        while code in seen_codes or PromotionCampaign.objects.exclude(pk=campaign.pk).filter(code=code).exists():
            code = f'{base_code}-{counter}'
            counter += 1
        campaign.code = code
        campaign.save(update_fields=['code'])
        seen_codes.add(code)


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0006_alter_availabilityblock_source_booking'),
        ('marketing', '0002_promocode_max_discount_amount'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql='DROP INDEX IF EXISTS "marketing_b_positio_ec98f5_idx";',
                    reverse_sql='CREATE INDEX IF NOT EXISTS "marketing_b_positio_ec98f5_idx" ON "marketing_banner" ("position", "is_active");',
                ),
            ],
            state_operations=[
                migrations.RemoveIndex(
                    model_name='banner',
                    name='marketing_b_positio_ec98f5_idx',
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql='DROP INDEX IF EXISTS "marketing_p_valid_f_b47bff_idx";',
                    reverse_sql='CREATE INDEX IF NOT EXISTS "marketing_p_valid_f_b47bff_idx" ON "marketing_promocode" ("valid_from", "valid_until");',
                ),
            ],
            state_operations=[
                migrations.RemoveIndex(
                    model_name='promocode',
                    name='marketing_p_valid_f_b47bff_idx',
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql='DROP INDEX IF EXISTS "marketing_p_start_d_af42f8_idx";',
                    reverse_sql='CREATE INDEX IF NOT EXISTS "marketing_p_start_d_af42f8_idx" ON "marketing_promotioncampaign" ("start_date", "end_date", "is_active");',
                ),
            ],
            state_operations=[
                migrations.RemoveIndex(
                    model_name='promotioncampaign',
                    name='marketing_p_start_d_af42f8_idx',
                ),
            ],
        ),
        migrations.AddField(
            model_name='promotioncampaign',
            name='code',
            field=models.SlugField(blank=True, max_length=50, null=True),
        ),
        migrations.RenameField(
            model_name='promotioncampaign',
            old_name='start_date',
            new_name='starts_at',
        ),
        migrations.RenameField(
            model_name='promotioncampaign',
            old_name='end_date',
            new_name='ends_at',
        ),
        migrations.RenameField(
            model_name='promocode',
            old_name='value',
            new_name='discount_value',
        ),
        migrations.RenameField(
            model_name='promocode',
            old_name='valid_from',
            new_name='starts_at',
        ),
        migrations.RenameField(
            model_name='promocode',
            old_name='valid_until',
            new_name='ends_at',
        ),
        migrations.RenameField(
            model_name='banner',
            old_name='position',
            new_name='placement',
        ),
        migrations.RenameField(
            model_name='banner',
            old_name='start_date',
            new_name='starts_at',
        ),
        migrations.RenameField(
            model_name='banner',
            old_name='end_date',
            new_name='ends_at',
        ),
        migrations.CreateModel(
            name='PromoCodeRedemption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discount_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='promo_code_redemptions', to='bookings.booking')),
                ('promo_code', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='redemptions', to='marketing.promocode')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='promo_code_redemptions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['promo_code', 'created_at'], name='marketing_p_promo_c_21c974_idx'),
                    models.Index(fields=['user', 'created_at'], name='marketing_p_user_id_6547f5_idx'),
                ],
            },
        ),
        migrations.AddField(
            model_name='referral',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='referral',
            name='referred_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='received_referrals', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(populate_campaign_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='promotioncampaign',
            name='code',
            field=models.SlugField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='promotioncampaign',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='promocode',
            name='discount_value',
            field=models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))]),
        ),
        migrations.AlterField(
            model_name='promocode',
            name='usage_limit',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name='promocode',
            name='min_booking_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10),
        ),
        migrations.AddIndex(
            model_name='promotioncampaign',
            index=models.Index(fields=['code'], name='marketing_p_code_42e3ba_idx'),
        ),
        migrations.AddIndex(
            model_name='promotioncampaign',
            index=models.Index(fields=['starts_at', 'ends_at', 'is_active'], name='marketing_p_starts__fb7764_idx'),
        ),
        migrations.AddIndex(
            model_name='promocode',
            index=models.Index(fields=['starts_at', 'ends_at'], name='marketing_p_starts__9dc642_idx'),
        ),
        migrations.AddIndex(
            model_name='banner',
            index=models.Index(fields=['placement', 'is_active'], name='marketing_b_placeme_737b69_idx'),
        ),
        migrations.AddIndex(
            model_name='banner',
            index=models.Index(fields=['starts_at', 'ends_at'], name='marketing_b_starts__38105b_idx'),
        ),
    ]
