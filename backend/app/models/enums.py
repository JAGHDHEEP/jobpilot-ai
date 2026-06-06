"""Shared enumerations used across ORM models and schemas."""
from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class ApplicationStatus(str, enum.Enum):
    saved = "saved"
    applied = "applied"
    interview = "interview"
    rejected = "rejected"
    offer = "offer"
    accepted = "accepted"
    withdrawn = "withdrawn"


class JobSource(str, enum.Enum):
    linkedin = "linkedin"
    naukri = "naukri"
    indeed = "indeed"
    foundit = "foundit"
    wellfound = "wellfound"
    glassdoor = "glassdoor"
    remotive = "remotive"
    arbeitnow = "arbeitnow"
    company = "company"
    manual = "manual"


class WorkMode(str, enum.Enum):
    any = "any"
    remote = "remote"
    hybrid = "hybrid"
    onsite = "onsite"


class EmploymentType(str, enum.Enum):
    full_time = "full_time"
    part_time = "part_time"
    contract = "contract"
    internship = "internship"
    temporary = "temporary"


class RemoteType(str, enum.Enum):
    onsite = "onsite"
    hybrid = "hybrid"
    remote = "remote"


class DocKind(str, enum.Enum):
    resume = "resume"
    cover_letter = "cover_letter"


class SkillCategory(str, enum.Enum):
    technical = "technical"
    soft = "soft"
    tool = "tool"
    framework = "framework"
