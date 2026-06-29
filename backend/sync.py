import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def run_full_sync():
    today = date.today()

    logger.info("=== Full sync started ===")

    try:
        from backend.services.garmin_service import sync_garmin_day
        # Sync last 3 days so a missed sync never permanently loses a ride
        days_to_sync = [today - timedelta(days=i) for i in range(3)]
        logger.info(f"Syncing Garmin: {days_to_sync[-1]} to {days_to_sync[0]}")
        for d in days_to_sync:
            sync_garmin_day(d)
        logger.info("Garmin sync complete")
    except Exception as e:
        logger.error(f"Garmin sync error: {e}", exc_info=True)

    try:
        from backend.services.whoop_service import sync_whoop_range, is_authorized
        if is_authorized():
            three_days_ago = today - timedelta(days=3)
            logger.info(f"Syncing WHOOP: {three_days_ago} to {today}")
            sync_whoop_range(three_days_ago, today)
            logger.info("WHOOP sync complete")
        else:
            logger.warning("WHOOP not authorized — visit /whoop/login")
    except Exception as e:
        logger.error(f"WHOOP sync error: {e}", exc_info=True)

    logger.info("=== Full sync finished ===")
