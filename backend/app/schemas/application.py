"""Application tracker schemas."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel

from app.models.enums import ApplicationStatus
from app.schemas.common import ORMModel
from app.schemas.job import JobOut


class ApplicationCreate(BaseModel):
    job_id: str
    status: ApplicationStatus = ApplicationStatus.saved
    resume_doc_id: str | None = None
    cover_doc_id: str | None = None
    notes: str | None = None


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    note: str | None = None


class ApplicationEventOut(ORMModel):
    id: str
    from_status: ApplicationStatus | None = None
    to_status: ApplicationStatus
    note: str | None = None
    created_at: dt.datetime


class ApplicationOut(ORMModel):
    id: str
    job_id: str
    status: ApplicationStatus
    resume_doc_id: str | None = None
    cover_doc_id: str | None = None
    notes: str | None = None
    applied_at: dt.datetime | None = None
    created_at: dt.datetime
    job: JobOut | None = None
    events: list[ApplicationEventOut] = []


class FunnelStats(BaseModel):
    saved: int = 0
    applied: int = 0
    interview: int = 0
    rejected: int = 0
    offer: int = 0
    accepted: int = 0
    withdrawn: int = 0


class ApplicationAnalytics(BaseModel):
    funnel: FunnelStats
    per_month: dict[str, int]
    success_rate: float           # offers / applied
    interview_rate: float         # interviews / applied
    total: int
