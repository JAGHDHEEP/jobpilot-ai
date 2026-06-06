"""Profile and its child collections."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, Date, Enum, ForeignKey, Integer, Numeric, String, Text, \
    UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base, TimestampMixin, UUIDMixin
from app.models.enums import SkillCategory


class Profile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    phone: Mapped[str | None] = mapped_column(String(40))
    location: Mapped[str | None] = mapped_column(String(200))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    github_url: Mapped[str | None] = mapped_column(String(500))
    portfolio_url: Mapped[str | None] = mapped_column(String(500))
    headline: Mapped[str | None] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(Text)
    languages: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Professional info (what recruiters ask for)
    current_role: Mapped[str | None] = mapped_column(String(200))
    years_experience: Mapped[float | None] = mapped_column(Numeric(4, 1))
    current_ctc: Mapped[str | None] = mapped_column(String(60))
    expected_ctc: Mapped[str | None] = mapped_column(String(60))
    notice_period: Mapped[str | None] = mapped_column(String(60))

    # Job preferences (drive search + ranking)
    work_mode: Mapped[str | None] = mapped_column(String(20))          # any|remote|hybrid|onsite
    preferred_locations: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    preferred_titles: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    salary_min: Mapped[float | None] = mapped_column(Numeric(12, 2))
    salary_max: Mapped[float | None] = mapped_column(Numeric(12, 2))

    user = relationship("User", back_populates="profile")
    educations: Mapped[list["Education"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan")
    experiences: Mapped[list["Experience"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan")
    skills: Mapped[list["Skill"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan")
    certifications: Mapped[list["Certification"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan")
    achievements: Mapped[list["Achievement"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan")


class Education(UUIDMixin, Base):
    __tablename__ = "educations"
    profile_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    degree: Mapped[str] = mapped_column(String(200), nullable=False)
    field_of_study: Mapped[str | None] = mapped_column(String(200))
    institution: Mapped[str] = mapped_column(String(300), nullable=False)
    gpa: Mapped[float | None] = mapped_column(Numeric(4, 2))
    start_year: Mapped[int | None] = mapped_column(Integer)
    graduation_year: Mapped[int | None] = mapped_column(Integer)

    profile = relationship("Profile", back_populates="educations")


class Experience(UUIDMixin, Base):
    __tablename__ = "experiences"
    profile_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    company: Mapped[str] = mapped_column(String(300), nullable=False)
    role: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[dt.date | None] = mapped_column(Date)
    end_date: Mapped[dt.date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    highlights: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    profile = relationship("Profile", back_populates="experiences")


class Project(UUIDMixin, Base):
    __tablename__ = "projects"
    profile_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    technologies: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    github_url: Mapped[str | None] = mapped_column(String(500))
    live_url: Mapped[str | None] = mapped_column(String(500))
    achievements: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    profile = relationship("Profile", back_populates="projects")


class Skill(UUIDMixin, Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("profile_id", "name"),)
    profile_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[SkillCategory] = mapped_column(
        Enum(SkillCategory), default=SkillCategory.technical, nullable=False)
    proficiency: Mapped[int | None] = mapped_column(Integer)
    years: Mapped[float | None] = mapped_column(Numeric(4, 1))

    profile = relationship("Profile", back_populates="skills")


class Certification(UUIDMixin, Base):
    __tablename__ = "certifications"
    profile_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(200))
    issue_date: Mapped[dt.date | None] = mapped_column(Date)
    expiry_date: Mapped[dt.date | None] = mapped_column(Date)
    credential_url: Mapped[str | None] = mapped_column(String(500))

    profile = relationship("Profile", back_populates="certifications")


class Achievement(UUIDMixin, Base):
    __tablename__ = "achievements"
    profile_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    date: Mapped[dt.date | None] = mapped_column(Date)

    profile = relationship("Profile", back_populates="achievements")
