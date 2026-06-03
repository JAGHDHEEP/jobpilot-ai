"""Job, match, and recommendation schemas."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from app.models.enums import EmploymentType, JobSource, RemoteType
from app.schemas.common import ORMModel


class JobBase(BaseModel):
    title: str
    company: str
    location: str | None = None
    remote_type: RemoteType | None = None
    employment_type: EmploymentType | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    description: str
    requirements: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    experience_min: float | None = None
    experience_max: float | None = None
    posted_at: dt.datetime | None = None
    apply_url: str | None = None
    company_rating: float | None = None


class JobCreate(JobBase):
    source: JobSource = JobSource.manual
    source_job_id: str | None = None


class JobOut(JobBase, ORMModel):
    id: str
    source: JobSource
    created_at: dt.datetime | None = None


class JobSearchQuery(BaseModel):
    q: str | None = None
    location: str | None = None
    remote_type: RemoteType | None = None
    sources: list[JobSource] | None = None
    min_salary: float | None = None
    posted_within_days: int | None = Field(None, ge=1, le=90)


class MatchScores(BaseModel):
    overall_score: int
    skill_score: int
    project_score: int
    experience_score: int
    education_score: int
    keyword_score: int


class MatchOut(MatchScores, ORMModel):
    id: str
    job_id: str
    missing_skills: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    rationale: str | None = None
    model_version: str | None = None


class MatchWithJob(BaseModel):
    match: MatchOut
    job: JobOut


class RecommendationOut(BaseModel):
    rank: int
    rank_score: float
    job: JobOut
    match: MatchOut | None = None
