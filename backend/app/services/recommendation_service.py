"""Daily recommendation engine: blend match score, freshness, salary, quality, remote."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RemoteType
from app.models.job import Job, JobMatch, Recommendation
from app.models.profile import Profile
from app.services.matching_service import match_user_against_jobs

# Blend weights (sum need not be 1; final is normalized by construction below).
W_MATCH, W_FRESH, W_SALARY, W_QUALITY, W_REMOTE, W_PREF = 0.50, 0.12, 0.10, 0.08, 0.07, 0.13


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


def _preference_fit(job: Job, profile: Profile | None) -> float:
    """0..1 how well the job matches the user's stated preferences."""
    if profile is None:
        return 0.5
    score, signals = 0.0, 0
    # Work mode
    if profile.work_mode and profile.work_mode != "any":
        signals += 1
        if job.remote_type and job.remote_type.value == profile.work_mode:
            score += 1
    # Preferred locations (substring match)
    locs = [str(x).lower() for x in (profile.preferred_locations or [])]
    if locs:
        signals += 1
        jl = (job.location or "").lower()
        if any(loc in jl or jl in loc for loc in locs) or "remote" in jl:
            score += 1
    # Preferred titles
    titles = [str(x).lower() for x in (profile.preferred_titles or [])]
    if titles:
        signals += 1
        jt = (job.title or "").lower()
        if any(any(w in jt for w in t.split()) for t in titles):
            score += 1
    # Salary expectation (job max >= user's min)
    if profile.salary_min and job.salary_max:
        signals += 1
        if float(job.salary_max) >= float(profile.salary_min):
            score += 1
    return score / signals if signals else 0.5


def rank_score(job: Job, match: JobMatch, profile: Profile | None = None) -> float:
    return round(
        W_MATCH * (match.overall_score / 100)
        + W_FRESH * _freshness(job.posted_at)
        + W_SALARY * _salary_signal(job)
        + W_QUALITY * _quality(job)
        + W_REMOTE * _remote(job)
        + W_PREF * _preference_fit(job, profile),
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

    profile = (await db.execute(
        select(Profile).where(Profile.user_id == user_id))).scalar_one_or_none()

    ranked = sorted(
        ((job, match_by_job[job.id]) for job in jobs if job.id in match_by_job),
        key=lambda pair: rank_score(pair[0], pair[1], profile),
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
