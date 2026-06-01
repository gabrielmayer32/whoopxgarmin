import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def run_full_sync():
    today = date.today()
    yesterday = today - timedelta(days=1)

    logger.info("=== Full sync started ===")

    try:
        from backend.services.garmin_service import sync_garmin_day
        logger.info(f"Syncing Garmin: {yesterday} and {today}")
        sync_garmin_day(today)
        sync_garmin_day(yesterday)
        logger.info("Garmin sync complete")
    except Exception as e:
        logger.error(f"Garmin sync error: {e}", exc_info=True)

    try:
        from backend.services.whoop_service import sync_whoop_range, is_authorized
        if is_authorized():
            logger.info(f"Syncing WHOOP: {yesterday} to {today}")
            sync_whoop_range(yesterday, today)
            logger.info("WHOOP sync complete")
        else:
            logger.warning("WHOOP not authorized — visit /whoop/login")
    except Exception as e:
        logger.error(f"WHOOP sync error: {e}", exc_info=True)

    try:
        from backend.services.strava_service import sync_strava_range, is_authorized as strava_authorized
        if strava_authorized():
            logger.info(f"Syncing Strava gym sessions: {yesterday} to {today}")
            sync_strava_range(yesterday, today)
            logger.info("Strava sync complete")
        else:
            logger.warning("Strava not authorized — visit /strava/login")
    except Exception as e:
        logger.error(f"Strava sync error: {e}", exc_info=True)

    logger.info("=== Full sync finished ===")
