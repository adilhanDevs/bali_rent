from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Booking
import logging

logger = logging.getLogger(__name__)

@shared_task
def expire_unpaid_bookings():
    """
    Finds bookings created more than 1 hour ago that are still 'pending' or 'created'
    and haven't been paid, then cancels them to release inventory.
    """
    threshold = timezone.now() - timedelta(hours=1)
    unpaid_bookings = Booking.objects.filter(
        status__in=['created', 'pending'],
        payment_status='pending',
        created_at__lt=threshold
    )
    
    count = unpaid_bookings.count()
    if count > 0:
        logger.info(f"Expiring {count} unpaid bookings.")
        # In a real scenario, we might want to log this via AuditService
        # and trigger notifications.
        unpaid_bookings.update(status='cancelled')
    
    return f"Expired {count} bookings."
