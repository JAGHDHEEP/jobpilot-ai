"""Application tracker: status transitions + analytics."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.models.application import Application, ApplicationEvent
from app.models.enums import ApplicationStatus
from app.schemas.application import ApplicationAnalytics, FunnelStats


async def create_application(db: AsyncSession, user_id: str, job_id: str,
                             status: ApplicationStatus, **kw) -> Application:
    existing = (await db.execute(
        select(Application).where(Application.user_id == user_id, Application.job_id == job_id)
    )).scalar_one_or_none()
    if existing:
        raise ConflictError("Application already exists for this job.")
    now = datetime.now(timezone.utc)
    app = Application(user_id=user_id, job_id=job_id, status=status,
                      applied_at=now if status == ApplicationStatus.applied else None, **kw)
    db.add(app)
    await db.flush()
    db.add(ApplicationEvent(application_id=app.id, from_status=None, to_status=status,
                            created_at=now))
    await db.flush()
    return await _load(db, user_id, str(app.id))


async def update_status(db: AsyncSession, user_id: str, app_id: str,
                        status: ApplicationStatus, note: str | None = None) -> Application:
    app = await _load(db, user_id, app_id)
    if app.status == status:
        return app
    now = datetime.now(timezone.utc)
    db.add(ApplicationEvent(application_id=app.id, from_status=app.status,
                            to_status=status, note=note, created_at=now))
    if status == ApplicationStatus.applied and app.applied_at is None:
        app.applied_at = now
    app.status = status
    await db.flush()
    return await _load(db, user_id, app_id)


async def list_applications(db: AsyncSession, user_id: str) -> list[Application]:
    stmt = (
        select(Application)
        .where(Application.user_id == user_id)
        .options(selectinload(Application.events))
        .order_by(Application.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def _load(db: AsyncSession, user_id: str, app_id: str) -> Application:
    stmt = (
        select(Application)
        .where(Application.id == app_id, Application.user_id == user_id)
        .options(selectinload(Application.events))
        .execution_options(populate_existing=True)   # refresh cached instance + events
    )
    app = (await db.execute(stmt)).scalar_one_or_none()
    if not app:
        raise NotFoundError("Application not found.")
    return app


async def analytics(db: AsyncSession, user_id: str) -> ApplicationAnalytics:
    rows = (await db.execute(
        select(Application.status, Application.created_at, Application.applied_at)
        .where(Application.user_id == user_id)
    )).all()

    funnel = FunnelStats()
    per_month: dict[str, int] = defaultdict(int)
    applied = interviews = offers = 0
    for status, created_at, applied_at in rows:
        setattr(funnel, status.value, getattr(funnel, status.value) + 1)
        month = (applied_at or created_at).strftime("%Y-%m")
        per_month[month] += 1
        if status in (ApplicationStatus.applied, ApplicationStatus.interview,
                      ApplicationStatus.offer, ApplicationStatus.accepted,
                      ApplicationStatus.rejected):
            applied += 1
        if status in (ApplicationStatus.interview, ApplicationStatus.offer,
                      ApplicationStatus.accepted):
            interviews += 1
        if status in (ApplicationStatus.offer, ApplicationStatus.accepted):
            offers += 1

    total = len(rows)
    return ApplicationAnalytics(
        funnel=funnel,
        per_month=dict(sorted(per_month.items())),
        success_rate=round(offers / applied, 3) if applied else 0.0,
        interview_rate=round(interviews / applied, 3) if applied else 0.0,
        total=total,
    )
