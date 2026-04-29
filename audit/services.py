from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection
from django.utils import timezone
from .models import AuditLog, AdminLoginLog
import json

class AuditService:
    @staticmethod
    def log_mutation(user, obj, action, before_dict=None, after_dict=None, ip_address=None, user_agent=None):
        content_type = ContentType.objects.get_for_model(obj)
        
        # Use DjangoJSONEncoder to handle dates/decimals before saving to JSONField
        # although JSONField usually handles this, the model_to_dict might contain objects
        # that need explicit conversion if the DB backend is strict.
        before_json = AuditService._serialize_dict(before_dict) if before_dict else {}
        after_json = AuditService._serialize_dict(after_dict) if after_dict else {}

        table_name = AuditLog._meta.db_table
        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, table_name)
            }

            payload = {
                'user_id': user.id if user else None,
                'content_type_id': content_type.id,
                'object_id': str(obj.pk),
                'action': action,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'created_at': timezone.now(),
            }

            if 'changes' in columns:
                payload['changes'] = json.dumps(after_json or before_json or {}, cls=DjangoJSONEncoder)
            if 'before_json' in columns:
                payload['before_json'] = json.dumps(before_json, cls=DjangoJSONEncoder)
            if 'after_json' in columns:
                payload['after_json'] = json.dumps(after_json, cls=DjangoJSONEncoder)

            insert_columns = ', '.join(payload.keys())
            placeholders = ', '.join(['%s'] * len(payload))
            cursor.execute(
                f'INSERT INTO {table_name} ({insert_columns}) VALUES ({placeholders})',
                list(payload.values()),
            )

        return None

    @staticmethod
    def log_action(user, obj, action, changes=None, before_dict=None, after_dict=None, ip_address=None, user_agent=None):
        """
        Backward-compatible wrapper for older call sites that still use
        `log_action(..., changes=...)` instead of the new snapshot API.
        """
        if changes is not None:
            after_dict = after_dict or changes

        return AuditService.log_mutation(
            user=user,
            obj=obj,
            action=action,
            before_dict=before_dict,
            after_dict=after_dict,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def log_admin_login(user, ip_address, user_agent, is_success=True):
        return AdminLoginLog.objects.create(
            user=user,
            ip_address=ip_address or '127.0.0.1',
            user_agent=user_agent or '',
            is_success=is_success
        )

    @staticmethod
    def _serialize_dict(data):
        if not data:
            return {}
            
        # Handle non-serializable objects like FieldFile before json.dumps
        serializable_data = {}
        from django.db.models.fields.files import FieldFile
        for key, value in data.items():
            if isinstance(value, FieldFile):
                serializable_data[key] = value.url if value else None
            else:
                serializable_data[key] = value

        # Convert to JSON and back to dict to ensure all types (date, decimal) 
        # are converted to JSON-serializable strings/numbers
        return json.loads(json.dumps(serializable_data, cls=DjangoJSONEncoder))
