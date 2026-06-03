"""Job persistence, dedupe, search, and embedding."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rag import index_job
from app.core.exceptions import NotFoundError
from app.models.job import Job
from app.schemas.job import JobCreate, JobSearchQuery


def content_hash(title: str, company: str, location: str | None) -> str:
    blob = f"{title.strip().lower()}|{company.strip().lower()}|{(location or '').strip().lower()}"
    return hashlib.sha256(blob.encode()).hexdigest()


async def upsert_job(db: AsyncSession, data: JobCreate) -> Job:
    chash = content_hash(data.title, data.company, data.location)
    existing = (await db.execute(
        select(Job).where(Job.source == data.source, Job.content_hash == chash)
    )).scalar_one_or_none()
    if existing:
        return existing
    job = Job(
        **data.model_dump(exclude={"source", "source_job_id"}),
        source=data.source, source_job_id=data.source_job_id,
        content_hash=chash, created_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()
    try:
        await index_job(str(job.id), job.title, job.description)
        job.embedded = True
        await db.flush()
    except Exception:  # pragma: no cover - embedding is best-effort
        pass
    return job


async def get_job(db: AsyncSession, job_id: str) -> Job:
    job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if not job:
        raise NotFoundError("Job not found.")
    return job


async def search_jobs(db: AsyncSession, query: JobSearchQuery, *, offset: int = 0,
                      limit: int = 20) -> tuple[list[Job], int]:
    stmt = select(Job)
    if query.q:
        like = f"%{query.q}%"
        stmt = stmt.where(or_(Job.title.ilike(like), Job.company.ilike(like),
                              Job.description.ilike(like)))
    if query.location:
        stmt = stmt.where(Job.location.ilike(f"%{query.location}%"))
    if query.remote_type:
        stmt = stmt.where(Job.remote_type == query.remote_type)
    if query.sources:
        stmt = stmt.where(Job.source.in_(query.sources))
    if query.min_salary:
        stmt = stmt.where(Job.salary_max >= query.min_salary)
    if query.posted_within_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=query.posted_within_days)
        stmt = stmt.where(Job.posted_at >= cutoff)

    from sqlalchemy import func
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(Job.posted_at.desc().nullslast()).offset(offset).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows), int(total)
