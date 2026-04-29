from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    soft_time_limit=30,
    time_limit=60,
)
def sync_currency_rates(self):
    """
    Mock task for syncing currency rates from an external API (e.g. fixer.io).
    """
    logger.info("Syncing currency rates", extra={"provider": "mock"})
    # Implementation would call an external API and update a Currency model
    return "Rates synced successfully (mock)."
