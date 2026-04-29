from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def sync_currency_rates():
    """
    Mock task for syncing currency rates from an external API (e.g. fixer.io).
    """
    logger.info("Syncing currency rates...")
    # Implementation would call an external API and update a Currency model
    return "Rates synced successfully (mock)."
