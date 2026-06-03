"""Daily recommendation engine: blend match score, freshness, salary, quality, remote."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RemoteType
from app.models.job import Job, JobMatch, Recommendation
from app.services.matching_service import match_user_against_jobs

# Blend weights (sum need not be 1; final is normalized by construction below).
W_MATCH, W_FRESH, W_SALARY, W_QUALITY, W_REMOTE = 0.55, 0.15, 0.12, 0.10, 0.08


def _freshness(posted_at: datetime | None) -> float:
    if not posted_at:
        return 0.4
    age_days = (datetime.now(timezone.utc) - posted_at).days
    return max(0.0, 1.0 - age_days / 30)            # linear decay over 30 days


def _salary_signal(job: Job) -> float:
    if not job.salary_max:
        return 0.4
    # squash to 0..1 around a 200k reference
    return min(1.0, float(job.salary_max) / 200_000)


def _quality(job: Job) -> float:
    return float(job.company_rating) / 5 if job.company_rating else 0.5


def _remote(job: Job) -> float:
    return {RemoteType.remote: 1.0, RemoteType.hybrid: 0.7,
            RemoteType.onsite: 0.4}.get(job.remote_type, 0.5)


def rank_score(job: Job, match: JobMatch) -> float:
    return round(
        W_MATCH * (match.overall_score / 100)
        + W_FRESH * _freshness(job.posted_at)
        + W_SALARY * _salary_signal(job)
        + W_QUALITY * _quality(job)
        + W_REMOTE * _remote(job),
        4,
    )


async def build_daily_recommendations(db: AsyncSession, user_id: str,
                                      top_n: int = 50, lookback_days: int = 14) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    jobs = list((await db.execute(
        select(Job).where((Job.posted_at >= cutoff) | (Job.posted_at.is_(None)))
        .order_by(Job.created_at.desc()).limit(500)
    )).scalars().all())
    if not jobs:
        return 0

    matches = await match_user_against_jobs(db, user_id, jobs)
    match_by_job = {m.job_id: m for m in matches}

    ranked = sorted(
        ((job, match_by_job[job.id]) for job in jobs if job.id in match_by_job),
        key=lambda pair: rank_score(pair[0], pair[1]),
        reverse=True,
    )[:top_n]

    today = date.today()
    await db.execute(
        delete(Recommendation).where(Recommendation.user_id == user_id,
                                     Recommendation.for_date == today)
    )
    now = datetime.now(timezone.utc)
    for rank, (job, match) in enumerate(ranked, start=1):
        db.add(Recommendation(
            user_id=user_id, job_id=job.id, for_date=today, rank=rank,
            rank_score=rank_score(job, match), created_at=now,
        ))
    await db.flush()
    return len(ranked)


async def get_recommendations(db: AsyncSession, user_id: str,
                              for_date: date | None = None) -> list[tuple[Recommendation, Job, JobMatch | None]]:
    target = for_date or date.today()
    recs = list((await db.execute(
        select(Recommendation)
        .where(Recommendation.user_id == user_id, Recommendation.for_date == target)
        .order_by(Recommendation.rank)
    )).scalars().all())
    if not recs:
        return []
    job_ids = [r.job_id for r in recs]
    jobs = {j.id: j for j in (await db.execute(
        select(Job).where(Job.id.in_(job_ids)))).scalars().all()}
    matches = {m.job_id: m for m in (await db.execute(
        select(JobMatch).where(JobMatch.user_id == user_id,
                               JobMatch.job_id.in_(job_ids)))).scalars().all()}
    return [(r, jobs[r.job_id], matches.get(r.job_id)) for r in recs if r.job_id in jobs]
