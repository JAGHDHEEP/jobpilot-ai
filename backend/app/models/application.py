"""Application tracking + status-transition history."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Enum, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base, TimestampMixin, UUIDMixin
from app.models.enums import ApplicationStatus


class Application(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "job_id"),)

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[str] = mapped_column(GUID(), ForeignKey("jobs.id", ondelete="CASCADE"))
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus), default=ApplicationStatus.saved, nullable=False)
    resume_doc_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="SET NULL"))
    cover_doc_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text)
    applied_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="application", cascade="all, delete-orphan",
        order_by="ApplicationEvent.created_at")


class ApplicationEvent(UUIDMixin, Base):
    __tablename__ = "application_events"

    application_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[ApplicationStatus | None] = mapped_column(Enum(ApplicationStatus))
    to_status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))

    application: Mapped[Application] = relationship(back_populates="events")
