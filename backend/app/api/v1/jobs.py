"""Job search, ingestion, matching, and daily recommendations."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DBSession
from app.connectors import enabled_connectors
from app.schemas.common import Message, Page
from app.schemas.job import (
    JobCreate,
    JobOut,
    JobSearchQuery,
    MatchOut,
    MatchWithJob,
    RecommendationOut,
)
from app.services import job_service, matching_service, recommendation_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=Page[JobOut])
async def search(
    db: DBSession,
    user: CurrentUser,
    q: str | None = None,
    location: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> Page[JobOut]:
    query = JobSearchQuery(q=q, location=location)
    rows, total = await job_service.search_jobs(db, query, offset=(page - 1) * size, limit=size)
    return Page[JobOut](
        items=[JobOut.model_validate(r, from_attributes=True) for r in rows],
        total=total, page=page, size=size,
    )


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
async def create_job(body: JobCreate, user: CurrentUser, db: DBSession) -> JobOut:
    job = await job_service.upsert_job(db, body)
    await db.commit()
    return JobOut.model_validate(job, from_attributes=True)


@router.post("/ingest", response_model=Message)
async def ingest(user: CurrentUser, db: DBSession,
                 q: str = "", location: str = "", limit: int = 30) -> Message:
    """Aggregate real jobs from enabled connectors on demand.

    With no explicit query, searches are driven by the user's preferred job titles
    (and top skills) so results are personalized — the core of the workflow.
    """
    from app.services import profile_service

    queries: list[str] = [q] if q else []
    if not queries:
        profile = await profile_service.get_profile(db, str(user.id))
        queries = list(profile.preferred_titles or [])
        if not queries and profile.skills:
            queries = [s.name for s in profile.skills[:3]]
        if not queries:
            queries = [""]  # fall back to latest jobs

    loc = location or ""
    count = 0
    seen_sources = set()
    for connector in enabled_connectors():
        seen_sources.add(connector.source.value)
        for query in queries[:5]:
            for item in await connector.fetch(query=query, location=loc, limit=limit):
                await job_service.upsert_job(db, item)
                count += 1
    await db.commit()
    return Message(
        message=f"Ingested {count} jobs from {len(seen_sources)} live sources "
                f"({', '.join(sorted(seen_sources))}).")


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, user: CurrentUser, db: DBSession) -> JobOut:
    job = await job_service.get_job(db, job_id)
    return JobOut.model_validate(job, from_attributes=True)


@router.post("/{job_id}/match", response_model=MatchOut)
async def match(job_id: str, user: CurrentUser, db: DBSession) -> MatchOut:
    job = await job_service.get_job(db, job_id)
    result = await matching_service.match_job(db, str(user.id), job)
    await db.commit()
    return MatchOut.model_validate(result, from_attributes=True)


@router.get("/matches/top", response_model=list[MatchWithJob])
async def top_matches(user: CurrentUser, db: DBSession,
                      limit: int = Query(20, ge=1, le=100)) -> list[MatchWithJob]:
    from sqlalchemy import select
    from app.models.job import Job, JobMatch
    rows = (await db.execute(
        select(JobMatch, Job).join(Job, Job.id == JobMatch.job_id)
        .where(JobMatch.user_id == user.id)
        .order_by(JobMatch.overall_score.desc()).limit(limit)
    )).all()
    return [
        MatchWithJob(match=MatchOut.model_validate(m, from_attributes=True),
                     job=JobOut.model_validate(j, from_attributes=True))
        for m, j in rows
    ]


@router.post("/{job_id}/apply", response_model=dict)
async def apply(job_id: str, user: CurrentUser, db: DBSession) -> dict:
    """One-click apply: record the application as 'applied' and return the external
    apply URL for the client to open. We never auto-submit the resume to third parties."""
    from app.models.enums import ApplicationStatus
    from app.services import application_service
    job = await job_service.get_job(db, job_id)
    try:
        await application_service.create_application(
            db, str(user.id), job_id, ApplicationStatus.applied)
    except Exception:
        await db.rollback()
        # already tracked → move it to applied
        from sqlalchemy import select
        from app.models.application import Application
        existing = (await db.execute(select(Application).where(
            Application.user_id == user.id, Application.job_id == job_id))).scalar_one_or_none()
        if existing:
            await application_service.update_status(
                db, str(user.id), str(existing.id), ApplicationStatus.applied)
    await db.commit()
    return {"apply_url": job.apply_url, "status": "applied"}


@router.post("/recommendations/build", response_model=Message)
async def build_recommendations(user: CurrentUser, db: DBSession) -> Message:
    n = await recommendation_service.build_daily_recommendations(db, str(user.id))
    await db.commit()
    return Message(message=f"Built {n} recommendations for today.")


@router.get("/recommendations/today", response_model=list[RecommendationOut])
async def todays_recommendations(user: CurrentUser, db: DBSession) -> list[RecommendationOut]:
    triples = await recommendation_service.get_recommendations(db, str(user.id), date.today())
    return [
        RecommendationOut(
            rank=rec.rank, rank_score=float(rec.rank_score),
            job=JobOut.model_validate(job, from_attributes=True),
            match=MatchOut.model_validate(match, from_attributes=True) if match else None,
        )
        for rec, job, match in triples
    ]
