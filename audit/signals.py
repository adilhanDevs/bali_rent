import logging

from django.contrib.auth.signals import user_logged_in
from django.db import OperationalError, ProgrammingError
from django.dispatch import receiver

from .services import AuditService

logger = logging.getLogger(__name__)

@receiver(user_logged_in)
def log_admin_login(sender, request, user, **kwargs):
    if user.is_staff or user.is_superuser:
        ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip:
            ip = ip.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR') or '127.0.0.1'
            
        try:
            AuditService.log_admin_login(
                user=user,
                ip_address=ip,
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        except (OperationalError, ProgrammingError):
            logger.exception('Skipping admin login audit because audit tables are unavailable')
