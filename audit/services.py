from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict
from django.core.serializers.json import DjangoJSONEncoder
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

        return AuditLog.objects.create(
            user=user,
            content_type=content_type,
            object_id=str(obj.pk),
            action=action,
            before_json=before_json,
            after_json=after_json,
            ip_address=ip_address,
            user_agent=user_agent
        )

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
