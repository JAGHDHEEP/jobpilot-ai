"""Profile and child-collection schemas."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from app.models.enums import SkillCategory
from app.schemas.common import ORMModel


# ---- Education
class EducationIn(BaseModel):
    degree: str
    field_of_study: str | None = None
    institution: str
    gpa: float | None = Field(None, ge=0, le=10)
    start_year: int | None = None
    graduation_year: int | None = None


class EducationOut(EducationIn, ORMModel):
    id: str


# ---- Experience
class ExperienceIn(BaseModel):
    company: str
    role: str
    location: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    is_current: bool = False
    description: str | None = None
    highlights: list[str] = Field(default_factory=list)


class ExperienceOut(ExperienceIn, ORMModel):
    id: str


# ---- Project
class ProjectIn(BaseModel):
    title: str
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    github_url: str | None = None
    live_url: str | None = None
    achievements: list[str] = Field(default_factory=list)


class ProjectOut(ProjectIn, ORMModel):
    id: str


# ---- Skill
class SkillIn(BaseModel):
    name: str
    category: SkillCategory = SkillCategory.technical
    proficiency: int | None = Field(None, ge=1, le=5)
    years: float | None = Field(None, ge=0)


class SkillOut(SkillIn, ORMModel):
    id: str


# ---- Certification
class CertificationIn(BaseModel):
    name: str
    issuer: str | None = None
    issue_date: dt.date | None = None
    expiry_date: dt.date | None = None
    credential_url: str | None = None


class CertificationOut(CertificationIn, ORMModel):
    id: str


# ---- Achievement
class AchievementIn(BaseModel):
    title: str
    description: str | None = None
    date: dt.date | None = None


class AchievementOut(AchievementIn, ORMModel):
    id: str


# ---- Language
class Language(BaseModel):
    name: str
    proficiency: str | None = None


# ---- Profile aggregate
class ProfileUpdate(BaseModel):
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    headline: str | None = None
    summary: str | None = None
    languages: list[Language] | None = None
    # Professional
    current_role: str | None = None
    years_experience: float | None = Field(None, ge=0)
    current_ctc: str | None = None
    expected_ctc: str | None = None
    notice_period: str | None = None
    # Preferences
    work_mode: str | None = None
    preferred_locations: list[str] | None = None
    preferred_titles: list[str] | None = None
    salary_min: float | None = None
    salary_max: float | None = None


class ProfileOut(ORMModel):
    id: str
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    headline: str | None = None
    summary: str | None = None
    languages: list[Language] = Field(default_factory=list)
    current_role: str | None = None
    years_experience: float | None = None
    current_ctc: str | None = None
    expected_ctc: str | None = None
    notice_period: str | None = None
    work_mode: str | None = None
    preferred_locations: list[str] = Field(default_factory=list)
    preferred_titles: list[str] = Field(default_factory=list)
    salary_min: float | None = None
    salary_max: float | None = None
    educations: list[EducationOut] = Field(default_factory=list)
    experiences: list[ExperienceOut] = Field(default_factory=list)
    projects: list[ProjectOut] = Field(default_factory=list)
    skills: list[SkillOut] = Field(default_factory=list)
    certifications: list[CertificationOut] = Field(default_factory=list)
    achievements: list[AchievementOut] = Field(default_factory=list)
