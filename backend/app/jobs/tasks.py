"""
Celery background tasks for daily price ingestion and health checks.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from backend.app.db.session import get_sync_db
from backend.app.jobs.celery_app import celery
from backend.app.models.price import Price
from backend.app.services.agmarknet import AgmarknetService

logger = logging.getLogger(__name__)


@celery.task(name="backend.app.jobs.tasks.fetch_and_ingest_ap_banana")
def fetch_and_ingest_ap_banana() -> dict[str, str | int]:
    """
    Background job to pull and ingest daily Banana prices for Andhra Pradesh.
    """
    logger.info("Starting daily Agmarknet Banana (Andhra Pradesh) fetch...")
    raw_records = asyncio.run(AgmarknetService.fetch_ap_banana_raw())

    db = get_sync_db()
    try:
        log_entry = AgmarknetService.ingest_records(db, raw_records)

        # Check for data staleness (>24 hours)
        latest_date = db.scalar(select(func.max(Price.price_date)).where(Price.crop_id == "banana"))

        is_stale = False
        if latest_date:
            now_utc = datetime.now(UTC).date()
            if (now_utc - latest_date) > timedelta(days=1):
                is_stale = True
                logger.error(
                    f"[ALERT] Newest Banana price data in DB is older than 24 hours: {latest_date}"
                )

        return {
            "status": log_entry.status,
            "upserted": log_entry.records_upserted,
            "failed": log_entry.records_failed,
            "is_stale": is_stale,
        }
    except Exception as e:
        logger.exception(f"[ALERT] Daily fetch job failed with error: {e}")
        return {"status": "failure", "error": str(e)}
    finally:
        db.close()
