from django.db import migrations


def cleanup_orphaned_rows(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())

    statements = []

    if {"pricing_pricecalculationlog", "bookings_booking"} <= existing_tables:
        statements.append(
            """
            UPDATE pricing_pricecalculationlog
            SET booking_id = NULL
            WHERE booking_id IS NOT NULL
              AND booking_id NOT IN (SELECT id FROM bookings_booking)
            """
        )

    if {"pricing_pricecalculationlog", "catalog_vehicle"} <= existing_tables:
        statements.append(
            """
            UPDATE pricing_pricecalculationlog
            SET scooter_id = NULL
            WHERE scooter_id IS NOT NULL
              AND scooter_id NOT IN (SELECT id FROM catalog_vehicle)
            """
        )

    if {"pricing_pricecalculationlog", "users_user"} <= existing_tables:
        statements.append(
            """
            UPDATE pricing_pricecalculationlog
            SET user_id = NULL
            WHERE user_id IS NOT NULL
              AND user_id NOT IN (SELECT id FROM users_user)
            """
        )

    if {"chat_chatthread", "users_user"} <= existing_tables:
        statements.append(
            """
            UPDATE chat_chatthread
            SET created_by_id = NULL
            WHERE created_by_id IS NOT NULL
              AND created_by_id NOT IN (SELECT id FROM users_user)
            """
        )

    if {"chat_chatmessage", "users_user"} <= existing_tables:
        statements.append(
            """
            DELETE FROM chat_chatmessage
            WHERE sender_id IS NOT NULL
              AND sender_id NOT IN (SELECT id FROM users_user)
            """
        )

    if {"chat_chatparticipant", "users_user"} <= existing_tables:
        statements.append(
            """
            DELETE FROM chat_chatparticipant
            WHERE user_id IS NOT NULL
              AND user_id NOT IN (SELECT id FROM users_user)
            """
        )

    if {"audit_auditlog", "users_user"} <= existing_tables:
        statements.append(
            """
            UPDATE audit_auditlog
            SET user_id = NULL
            WHERE user_id IS NOT NULL
              AND user_id NOT IN (SELECT id FROM users_user)
            """
        )

    if {"analytics_analyticsevent", "users_user"} <= existing_tables:
        statements.append(
            """
            UPDATE analytics_analyticsevent
            SET user_id = NULL
            WHERE user_id IS NOT NULL
              AND user_id NOT IN (SELECT id FROM users_user)
            """
        )

    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


class Migration(migrations.Migration):

    dependencies = [
        ("pricing", "0003_rename_pricing_sea_code_16da58_idx_pricing_sea_code_77a776_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(cleanup_orphaned_rows, migrations.RunPython.noop),
    ]
