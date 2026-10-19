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
        # Multi-Source Mandi Price Ingestion 4 times a day (06:30, 11:30, 16:30, 20:30 IST)
        "multi-source-mandi-price-sync": {
            "task": "backend.app.jobs.tasks.run_multi_source_price_sync",
            "schedule": crontab(hour="6,11,16,20", minute=30),
        },
        # Daily 07:00 AM IST WhatsApp Price Broadcast to subscribed users
        "daily-whatsapp-price-broadcast": {
            "task": "backend.app.jobs.tasks.broadcast_daily_whatsapp_prices",
            "schedule": crontab(hour=7, minute=0),
        },
    },
)

celery.autodiscover_tasks(["backend.app.jobs"])
