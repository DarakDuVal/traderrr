"""
Celery application instance with Redis broker.
"""

from celery import Celery
from celery.schedules import crontab

from config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "traderrr",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # Retry configuration
    task_default_retry_delay=60,
    task_max_retries=3,
)

# ── Celery Beat schedule ──────────────────────────────────────────────────
celery_app.conf.beat_schedule = {
    "fetch-all-tickers-15min": {
        "task": "app.workers.market_data.fetch_all_tickers",
        "schedule": crontab(minute="*/15"),  # every 15 min during market hours
    },
    "generate-all-signals-15min": {
        "task": "app.workers.signals.generate_all_signals",
        "schedule": crontab(minute="*/15"),
    },
    "daily-cleanup": {
        "task": "app.workers.market_data.cleanup_old_data",
        "schedule": crontab(hour=2, minute=0),  # 2 AM daily
    },
}

# Auto-discover task modules
celery_app.autodiscover_tasks(["app.workers"])
