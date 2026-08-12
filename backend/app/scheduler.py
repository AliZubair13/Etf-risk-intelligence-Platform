"""
Background scheduler for automatic daily data refresh.
Runs price ingestion once per day after market close, so the platform
stays current without manual intervention.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.database.connection import SessionLocal
from app.ingestion.market_data import ingest_all_prices

logger = logging.getLogger(__name__)

def daily_price_refresh():
    logger.info("Running scheduled daily price refresh...")
    db = SessionLocal()
    try:
        total = ingest_all_prices(db)
        logger.info(f"Scheduled refresh complete: {total} rows inserted")
    except Exception as e:
        logger.error(f"Scheduled refresh failed: {e}")
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler(timezone="America/New_York")
    scheduler.add_job(daily_price_refresh, "cron", day_of_week="mon-fri", hour=16, minute=30)
    scheduler.start()
    logger.info("Scheduler started - daily price refresh at 4:30 PM ET, Mon-Fri")
    return scheduler
