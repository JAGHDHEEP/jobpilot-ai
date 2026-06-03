"""Job, match, and recommendation models."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, \
    String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import GUID, Base, TimestampMixin, UUIDMixin
from app.models.enums import EmploymentType, JobSource, RemoteType


class Job(UUIDMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("source", "content_hash"),)

    source: Mapped[JobSource] = mapped_column(Enum(JobSource), nullable=False)
    source_job_id: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    company: Mapped[str] = mapped_column(String(400), nullable=False)
    location: Mapped[str | None] = mapped_column(String(300))
    remote_type: Mapped[RemoteType | None] = mapped_column(Enum(RemoteType))
    employment_type: Mapped[EmploymentType | None] = mapped_column(Enum(EmploymentType))
    salary_min: Mapped[float | None] = mapped_column(Numeric(12, 2))
    salary_max: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(8))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    keywords: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    experience_min: Mapped[float | None] = mapped_column(Numeric(4, 1))
    experience_max: Mapped[float | None] = mapped_column(Numeric(4, 1))
    posted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    apply_url: Mapped[str | None] = mapped_column(String(1000))
    company_rating: Mapped[float | None] = mapped_column(Numeric(3, 2))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))


class JobMatch(UUIDMixin, Base):
    __tablename__ = "job_matches"
    __table_args__ = (UniqueConstraint("user_id", "job_id"),)

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[str] = mapped_column(GUID(), ForeignKey("jobs.id", ondelete="CASCADE"))
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    skill_score: Mapped[int] = mapped_column(Integer, nullable=False)
    project_score: Mapped[int] = mapped_column(Integer, nullable=False)
    experience_score: Mapped[int] = mapped_column(Integer, nullable=False)
    education_score: Mapped[int] = mapped_column(Integer, nullable=False)
    keyword_score: Mapped[int] = mapped_column(Integer, nullable=False)
    missing_skills: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    missing_keywords: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))


class Recommendation(UUIDMixin, Base):
    __tablename__ = "recommendations"
    __table_args__ = (UniqueConstraint("user_id", "job_id", "for_date"),)

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[str] = mapped_column(GUID(), ForeignKey("jobs.id", ondelete="CASCADE"))
    for_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    rank_score: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
