from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .services import AuditService

@receiver(user_logged_in)
def log_admin_login(sender, request, user, **kwargs):
    if user.is_staff or user.is_superuser:
        ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip:
            ip = ip.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
            
        AuditService.log_admin_login(
            user=user,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
