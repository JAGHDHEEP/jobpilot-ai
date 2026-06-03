"""Celery application + beat schedule."""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "jobpilot",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    worker_max_tasks_per_child=200,
)

celery_app.conf.beat_schedule = {
    "aggregate-jobs-hourly": {
        "task": "app.workers.tasks.aggregate_jobs",
        "schedule": crontab(minute=0),
    },
    "score-new-jobs": {
        "task": "app.workers.tasks.score_new_jobs",
        "schedule": crontab(minute="*/15"),
    },
    "daily-recommendations": {
        "task": "app.workers.tasks.build_daily_recommendations",
        "schedule": crontab(hour=6, minute=0),
    },
}
