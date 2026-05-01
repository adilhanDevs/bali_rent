from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Booking
import logging

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    soft_time_limit=30,
    time_limit=60,
)
def expire_unpaid_bookings(self):
    """
    Finds bookings created more than 1 hour ago that are still 'pending' or 'created'
    and haven't been paid, then cancels them to release inventory.
    """
    threshold = timezone.now() - timedelta(hours=1)
    unpaid_bookings = Booking.objects.filter(
        status__in=['created', 'pending_payment'],
        payment_status='pending',
        created_at__lt=threshold
    )
    
    count = unpaid_bookings.count()
    if count > 0:
        booking_ids = list(unpaid_bookings.values_list('id', flat=True))
        logger.info("Expiring unpaid bookings", extra={"booking_count": count, "booking_ids": booking_ids})
        Booking.objects.filter(id__in=booking_ids, status__in=['created', 'pending_payment']).update(status='cancelled')
        from .models import AvailabilityBlock
        AvailabilityBlock.objects.filter(source_booking_id__in=booking_ids, type='booking').delete()
    
    return f"Expired {count} bookings."
