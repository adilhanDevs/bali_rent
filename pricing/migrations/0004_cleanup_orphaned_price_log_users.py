from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pricing", "0003_rename_pricing_sea_code_16da58_idx_pricing_sea_code_77a776_idx_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                UPDATE pricing_pricecalculationlog
                SET booking_id = NULL
                WHERE booking_id IS NOT NULL
                  AND booking_id NOT IN (SELECT id FROM bookings_booking);

                UPDATE pricing_pricecalculationlog
                SET scooter_id = NULL
                WHERE scooter_id IS NOT NULL
                  AND scooter_id NOT IN (SELECT id FROM catalog_vehicle);

                UPDATE pricing_pricecalculationlog
                SET user_id = NULL
                WHERE user_id IS NOT NULL
                  AND user_id NOT IN (SELECT id FROM users_user);

                UPDATE chat_chatthread
                SET created_by_id = NULL
                WHERE created_by_id IS NOT NULL
                  AND created_by_id NOT IN (SELECT id FROM users_user);

                DELETE FROM chat_chatmessage
                WHERE sender_id IS NOT NULL
                  AND sender_id NOT IN (SELECT id FROM users_user);

                DELETE FROM chat_chatparticipant
                WHERE user_id IS NOT NULL
                  AND user_id NOT IN (SELECT id FROM users_user);

                UPDATE audit_auditlog
                SET user_id = NULL
                WHERE user_id IS NOT NULL
                  AND user_id NOT IN (SELECT id FROM users_user);

                UPDATE analytics_analyticsevent
                SET user_id = NULL
                WHERE user_id IS NOT NULL
                  AND user_id NOT IN (SELECT id FROM users_user);
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
