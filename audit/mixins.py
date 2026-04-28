from .services import AuditService
from django.forms.models import model_to_dict

class AuditMixin:
    """
    Mixin for ViewSets to automatically log mutations.
    """
    def perform_create(self, serializer):
        instance = serializer.save()
        self._log_audit(instance, 'create', after_dict=model_to_dict(instance))

    def perform_update(self, serializer):
        before_dict = model_to_dict(serializer.instance)
        instance = serializer.save()
        self._log_audit(instance, 'update', before_dict=before_dict, after_dict=model_to_dict(instance))

    def perform_destroy(self, instance):
        before_dict = model_to_dict(instance)
        instance_id = instance.pk
        instance.delete()
        # Create a mock-like object for content type resolution if needed, or just pass class
        self._log_audit(instance, 'delete', before_dict=before_dict)

    def _log_audit(self, instance, action, before_dict=None, after_dict=None):
        user = self.request.user if hasattr(self, 'request') and self.request.user.is_authenticated else None
        
        ip = None
        ua = None
        if hasattr(self, 'request'):
            x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = self.request.META.get('REMOTE_ADDR')
            ua = self.request.META.get('HTTP_USER_AGENT')

        AuditService.log_mutation(
            user=user,
            obj=instance,
            action=action,
            before_dict=before_dict,
            after_dict=after_dict,
            ip_address=ip,
            user_agent=ua
        )
