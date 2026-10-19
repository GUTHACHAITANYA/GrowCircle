"""
Data freshness, source health, and pipeline observability endpoint (/health/data).
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.session import get_async_db
from backend.app.models.ingestion import IngestionLog
from backend.app.models.mandi import Mandi
from backend.app.models.price import Price

router = APIRouter(prefix="/health", tags=["Data Health"])


@router.get("/data")
async def get_data_health(
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """
    Returns real-time data freshness, last successful fetch per source and state,
    total mandis reporting today, and alerts if prices are older than 24 hours.
    """
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    yesterday = today - timedelta(days=1)

    # 1. Latest price date in entire DB
    latest_price_date = await db.scalar(select(func.max(Price.price_date)))
    is_stale_alert = False
    alert_msg = None

    if latest_price_date:
        if latest_price_date < yesterday:
            is_stale_alert = True
            days_old = (today - latest_price_date).days
            alert_msg = f"Data staleness alert: Latest price in database is from {latest_price_date} ({days_old} days old > 24 hours)."
    else:
        is_stale_alert = True
        alert_msg = "No price data recorded in database."

    # 2. Number of mandis reporting today
    mandis_reporting_today = (
        await db.scalar(
            select(func.count(func.distinct(Price.mandi_id))).where(
                Price.price_date == today,
                Price.anomaly_status.in_(["clean", "approved", "auto_cleared"]),
            )
        )
    ) or 0

    # 3. Sources breakdown
    sources_summary: dict[str, Any] = {}
    known_sources = ["data.gov.in", "ceda_ashoka", "agmarknet_portal_csv"]
    for src in known_sources:
        latest_fetch = await db.scalar(
            select(func.max(Price.fetched_at)).where(Price.source == src)
        )
        total_recs = (
            await db.scalar(select(func.count(Price.id)).where(Price.source == src))
        ) or 0
        sources_summary[src] = {
            "last_successful_fetch": latest_fetch.isoformat() if latest_fetch else None,
            "total_records": total_recs,
            "status": "connected" if total_recs > 0 else "no_data",
        }

    # 4. State-level breakdown
    states_summary: dict[str, Any] = {}
    active_states_rows = (
        await db.execute(
            select(Mandi.state, func.max(Price.price_date), func.count(func.distinct(Price.mandi_id)))
            .join(Price, Mandi.id == Price.mandi_id)
            .group_by(Mandi.state)
        )
    ).all()

    for st_name, max_dt, mandi_cnt in active_states_rows:
        today_mandi_cnt = (
            await db.scalar(
                select(func.count(func.distinct(Price.mandi_id)))
                .join(Mandi, Price.mandi_id == Mandi.id)
                .where(Mandi.state == st_name, Price.price_date == today)
            )
        ) or 0
        states_summary[st_name] = {
            "last_reported_date": max_dt.isoformat() if max_dt else None,
            "total_mandis_with_history": mandi_cnt,
            "mandis_reporting_today": today_mandi_cnt,
            "is_stale": max_dt < yesterday if max_dt else True,
        }

    # 5. Data quality review queue counters
    quarantined_count = (
        await db.scalar(
            select(func.count(Price.id)).where(Price.anomaly_status.like("quarantined_%"))
        )
    ) or 0

    discrepancy_count = (
        await db.scalar(
            select(func.count(Price.id)).where(Price.anomaly_status == "source_discrepancy")
        )
    ) or 0

    status = "healthy" if not is_stale_alert and mandis_reporting_today > 0 else "degraded"

    return {
        "status": status,
        "overall_healthy": (status == "healthy"),
        "app_mode": settings.APP_MODE,
        "as_of": datetime.now(UTC).isoformat(),
        "latest_price_date": latest_price_date.isoformat() if latest_price_date else None,
        "mandis_reporting_today": mandis_reporting_today,
        "is_stale_alert": is_stale_alert,
        "alert_message": alert_msg,
        "stale_alerts": [alert_msg] if is_stale_alert and alert_msg else [],
        "sources": sources_summary,
        "states": states_summary,
        "quality_metrics": {
            "quarantined_errors_count": quarantined_count,
            "source_discrepancies_count": discrepancy_count,
        },
    }
