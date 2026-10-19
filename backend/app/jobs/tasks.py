"""
Celery background tasks for daily price ingestion and health checks.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

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


@celery.task(name="backend.app.jobs.tasks.broadcast_daily_whatsapp_prices")
def broadcast_daily_whatsapp_prices() -> dict[str, str | int]:
    """
    Scheduled 07:00 AM IST task to deliver daily mandi price alerts via WhatsApp Cloud API
    using approved message templates to users with active DPDP Act consent.
    """
    from backend.app.models.mandi import Mandi
    from backend.app.models.user import User
    from backend.app.services.speech.pronunciation import (
        get_crop_spoken_name,
        get_mandi_spoken_name,
    )
    from backend.app.services.whatsapp.handler import get_whatsapp_provider

    logger.info("Starting 07:00 AM WhatsApp daily price alert broadcast...")
    db = get_sync_db()
    provider = get_whatsapp_provider()
    sent_count = 0
    failed_count = 0

    try:
        # Find all subscribed users with explicit consent
        users = db.scalars(select(User).where(User.consent_at.isnot(None))).all()

        today_date = datetime.now(UTC).date()

        for user in users:
            lang = user.language or "te"
            district = user.district or "Guntur"
            crop_name = get_crop_spoken_name("banana", lang)

            # Query latest prices for this district
            stmt = (
                select(Price, Mandi)
                .join(Mandi, Price.mandi_id == Mandi.id)
                .where(
                    Price.crop_id == "banana",
                    func.lower(Mandi.district) == district.lower(),
                )
                .order_by(Price.price_date.desc())
                .limit(3)
            )
            rows = db.execute(stmt).all()

            if not rows:
                continue

            top_mandi_price = rows[0][0].modal_price_kg
            mandi_names = [get_mandi_spoken_name(m.id, m.name, lang) for _, m in rows]
            mandis_summary = ", ".join(mandi_names)

            # Formulate approved template parameters
            template_components = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": crop_name},
                        {"type": "text", "text": district.capitalize()},
                        {"type": "text", "text": f"₹{top_mandi_price:.2f}/kg"},
                        {"type": "text", "text": mandis_summary},
                        {"type": "text", "text": today_date.isoformat()},
                    ],
                }
            ]

            try:
                asyncio.run(
                    provider.send_template_message(
                        to_phone=user.phone,
                        template_name="daily_mandi_price_alert",
                        language_code=lang,
                        components=template_components,
                    )
                )
                sent_count += 1
            except Exception as send_err:
                logger.warning(
                    "Failed to deliver WhatsApp broadcast to %s: %s",
                    user.phone,
                    send_err,
                )
                failed_count += 1

        logger.info(
            "Completed WhatsApp broadcast. Sent: %d, Failed: %d",
            sent_count,
            failed_count,
        )
        return {"status": "success", "sent": sent_count, "failed": failed_count}

    except Exception as ex:
        logger.exception("Daily WhatsApp broadcast encountered error: %s", ex)
        return {"status": "error", "error": str(ex), "sent": sent_count}
    finally:
        db.close()


@celery.task(name="backend.app.jobs.tasks.nightly_rescore_and_model_promotion")
def nightly_rescore_and_model_promotion() -> dict[str, Any]:
    """
    Scheduled nightly task to re-score forecasting models against newly ingested mandi prices.
    Promotes candidate model ONLY if it beats current production baseline on expanding backtest.
    Logs run metrics and artifact state to MLflow.
    """
    logger.info("Starting nightly ML price forecasting re-scoring and promotion job...")
    try:
        import mlflow

        from ml.evaluation.backtest import RollingOriginBacktester

        bt = RollingOriginBacktester()
        results = bt.run_backtest()

        # Check promotion condition: LightGBM must beat seasonal naive across all horizons
        promoted = results["overall_lgb_beats_baseline"]
        avg_mase = float(
            sum(results["horizons"][h]["models"]["lightgbm_global"]["mase"] for h in results["horizons"])
            / len(results["horizons"])
        )

        # Log promotion decision to MLflow
        try:
            mlflow.set_tracking_uri("sqlite:///mlruns/mlflow.db")
            mlflow.set_experiment("growcircle_mandi_price_foundation")
            with mlflow.start_run(run_name="nightly_rescore_promotion"):
                mlflow.log_params({"job": "nightly_rescore", "promoted": str(promoted)})
                mlflow.log_metrics({"overall_avg_mase": avg_mase})
                mlflow.set_tags({"promotion_status": "PROMOTED" if promoted else "REJECTED"})
        except Exception as ml_err:
            logger.warning(f"MLflow logging warning during nightly job: {ml_err}")

        logger.info(
            f"Nightly re-scoring completed. Promoted: {promoted}, Average MASE: {avg_mase:.3f}"
        )
        return {
            "status": "success",
            "promoted": promoted,
            "average_mase": avg_mase,
            "horizons_evaluated": list(results["horizons"].keys()),
        }
    except Exception as e:
        logger.exception(f"Error during nightly ML re-scoring: {e}")
        return {"status": "error", "error": str(e)}


@celery.task(name="backend.app.jobs.tasks.run_multi_source_price_sync")
def run_multi_source_price_sync(state: str = "Andhra Pradesh") -> dict[str, Any]:
    """
    Ingests and reconciles real mandi prices across configured adapters:
    1. Official Agmarknet Portal CSV drops (Priority 1)
    2. data.gov.in Agmarknet API (Priority 2)
    3. CEDA Agri Market dataset (Priority 3)
    """
    logger.info(f"Starting scheduled multi-source price sync for state='{state}'...")
    from backend.app.services.price_sources.agmarknet_csv_adapter import AgmarknetPortalCsvAdapter
    from backend.app.services.price_sources.ceda_adapter import CedaAgriAdapter
    from backend.app.services.price_sources.data_gov_adapter import DataGovInAdapter
    from backend.app.services.price_sources.reconciler import PriceReconciler

    portal_adapter = AgmarknetPortalCsvAdapter()
    data_gov_adapter = DataGovInAdapter()
    ceda_adapter = CedaAgriAdapter()

    async def _gather_records():
        records = []
        # Ingest portal CSVs first
        csv_recs = await portal_adapter.fetch_prices(state=state)
        records.extend(csv_recs)

        # Ingest live data.gov.in
        dg_recs = await data_gov_adapter.fetch_prices(state=state)
        records.extend(dg_recs)

        # Ingest CEDA if available
        ceda_recs = await ceda_adapter.fetch_prices(state=state)
        records.extend(ceda_recs)
        return records

    all_records = asyncio.run(_gather_records())

    db = get_sync_db()
    try:
        reconciler = PriceReconciler(db)
        stats = reconciler.reconcile_and_save(all_records)
        logger.info(f"Multi-source price sync completed: {stats}")
        return {"status": "success", "stats": stats}
    except Exception as e:
        logger.exception(f"Multi-source price sync failed: {e}")
        return {"status": "failure", "error": str(e)}
    finally:
        db.close()


