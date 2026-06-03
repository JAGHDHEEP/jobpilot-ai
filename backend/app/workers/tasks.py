"""Celery tasks. Sync entrypoints that drive async service code via asyncio.run."""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.connectors import enabled_connectors
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.job import Job, JobMatch
from app.models.user import User
from app.services import job_service, matching_service, recommendation_service
from app.workers.celery_app import celery_app

log = get_logger()


def _run(coro):
    return asyncio.run(coro)


@celery_app.task(name="app.workers.tasks.aggregate_jobs")
def aggregate_jobs(query: str = "", location: str = "", limit: int = 50) -> int:
    async def _job() -> int:
        count = 0
        async with SessionLocal() as db:
            for connector in enabled_connectors():
                for item in await connector.fetch(query=query, location=location, limit=limit):
                    await job_service.upsert_job(db, item)
                    count += 1
            await db.commit()
        log.info("aggregate_jobs_done", count=count)
        return count

    return _run(_job())


@celery_app.task(name="app.workers.tasks.score_new_jobs")
def score_new_jobs(per_user_limit: int = 200) -> int:
    async def _job() -> int:
        scored = 0
        async with SessionLocal() as db:
            users = (await db.execute(select(User).where(User.is_active.is_(True)))).scalars().all()
            jobs = (await db.execute(select(Job).order_by(Job.created_at.desc())
                                     .limit(per_user_limit))).scalars().all()
            for user in users:
                existing = {m.job_id for m in (await db.execute(
                    select(JobMatch).where(JobMatch.user_id == user.id))).scalars().all()}
                todo = [j for j in jobs if j.id not in existing]
                if todo:
                    try:
                        await matching_service.match_user_against_jobs(db, str(user.id), todo)
                        scored += len(todo)
                    except Exception as exc:  # profile may be empty
                        log.info("score_skip_user", user=str(user.id), reason=str(exc))
            await db.commit()
        log.info("score_new_jobs_done", scored=scored)
        return scored

    return _run(_job())


@celery_app.task(name="app.workers.tasks.build_daily_recommendations")
def build_daily_recommendations() -> int:
    async def _job() -> int:
        total = 0
        async with SessionLocal() as db:
            users = (await db.execute(select(User).where(User.is_active.is_(True)))).scalars().all()
            for user in users:
                try:
                    total += await recommendation_service.build_daily_recommendations(
                        db, str(user.id))
                except Exception as exc:
                    log.info("rec_skip_user", user=str(user.id), reason=str(exc))
            await db.commit()
        log.info("daily_recommendations_done", total=total)
        return total

    return _run(_job())
