"""
Celery configuration and beat scheduler.
"""

from celery import Celery
from celery.schedules import crontab

from backend.app.core.config import settings

celery = Celery(
    "growcircle_jobs",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery.conf.update(
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    beat_schedule={
        # Daily Mandi Price Ingestion at 06:30 AM IST (01:00 UTC)
        "daily-ap-banana-fetch": {
            "task": "backend.app.jobs.tasks.fetch_and_ingest_ap_banana",
            "schedule": crontab(hour=6, minute=30),
        },
    },
)

celery.autodiscover_tasks(["backend.app.jobs"])
