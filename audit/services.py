from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.contenttypes.models import ContentType
from django.db import connection, transaction
from django.utils import timezone
from .models import AuditLog, AdminLoginLog
import json


SENSITIVE_KEY_PARTS = (
    'password',
    'passwd',
    'token',
    'secret',
    'authorization',
    'signature',
    'api_key',
    'apikey',
    'provider_key',
    'hash',
)


def redact_sensitive_data(value):
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if any(part in key_text for part in SENSITIVE_KEY_PARTS):
                redacted[key] = '********'
            else:
                redacted[key] = redact_sensitive_data(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive_data(item) for item in value)
    return value

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
    def log_webhook(provider, event_id, event_type, payload=None, status='pending', error_message='', processing_time_ms=None):
        from .models import WebhookProcessingLog
        return WebhookProcessingLog.objects.create(
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            payload_json=redact_sensitive_data(payload or {}),
            status=status,
            error_message=error_message,
            processing_time_ms=processing_time_ms
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
        return redact_sensitive_data(json.loads(json.dumps(serializable_data, cls=DjangoJSONEncoder)))


class WebhookLogService:
    @staticmethod
    def _event_id_from_payload(payload, raw_body=b''):
        event_id = payload.get('id') or payload.get('event_id') or payload.get('external_event_id')
        if event_id:
            return str(event_id)

        import hashlib
        seed = raw_body or json.dumps(payload, sort_keys=True, cls=DjangoJSONEncoder).encode()
        return hashlib.sha256(seed).hexdigest()

    @staticmethod
    @transaction.atomic
    def begin(provider, payload, raw_body=b'', event_type=None):
        from .models import WebhookProcessingLog

        payload = payload if isinstance(payload, dict) else {}
        event_id = WebhookLogService._event_id_from_payload(payload, raw_body)
        resolved_event_type = event_type or payload.get('type') or payload.get('event_type') or payload.get('status') or 'unknown'
        event, created = WebhookProcessingLog.objects.select_for_update().get_or_create(
            provider=provider,
            event_id=event_id,
            defaults={
                'event_type': resolved_event_type,
                'payload_json': redact_sensitive_data(payload),
            },
        )
        if not created:
            update_fields = []
            if not event.payload_json:
                event.payload_json = redact_sensitive_data(payload)
                update_fields.append('payload_json')
            if event.event_type == 'unknown' and resolved_event_type != 'unknown':
                event.event_type = resolved_event_type
                update_fields.append('event_type')
            if update_fields:
                event.save(update_fields=update_fields)
        return event, created

    @staticmethod
    def mark_success(event, started_at=None):
        event.processed = True
        event.processed_at = timezone.now()
        event.status = 'success'
        if started_at is not None:
            event.processing_time_ms = int((timezone.now() - started_at).total_seconds() * 1000)
        event.save(update_fields=['processed', 'processed_at', 'status', 'processing_time_ms'])
        return event

    @staticmethod
    def mark_failure(event, error_message, started_at=None):
        event.status = 'failure'
        event.error_message = str(error_message)
        if started_at is not None:
            event.processing_time_ms = int((timezone.now() - started_at).total_seconds() * 1000)
        event.save(update_fields=['status', 'error_message', 'processing_time_ms'])
        return event
