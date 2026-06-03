"""Document, resume-review, optimization, cover-letter, interview schemas."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from app.models.enums import DocKind
from app.schemas.common import ORMModel


class DocumentOut(ORMModel):
    id: str
    kind: DocKind
    title: str
    mime_type: str | None = None
    size_bytes: int | None = None
    is_master: bool
    job_id: str | None = None
    created_at: dt.datetime


class ParsedProfile(BaseModel):
    """Structured master profile extracted from a resume."""
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experiences: list[dict] = Field(default_factory=list)
    educations: list[dict] = Field(default_factory=list)
    projects: list[dict] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class ResumeReviewSection(BaseModel):
    name: str
    score: int
    feedback: str


class ResumeReview(BaseModel):
    ats_score: int = Field(ge=0, le=100)
    formatting_score: int
    keyword_score: int
    impact_score: int
    project_quality_score: int
    skill_relevance_score: int
    sections: list[ResumeReviewSection]
    suggestions: list[str]


class OptimizeRequest(BaseModel):
    job_id: str
    master_doc_id: str | None = None   # defaults to master resume


class OptimizedResume(BaseModel):
    job_id: str
    markdown: str
    added_keywords: list[str]
    document_id: str | None = None     # set once rendered to PDF & stored


class CoverLetterRequest(BaseModel):
    job_id: str
    tone: str = "professional"


class CoverLetter(BaseModel):
    job_id: str
    body: str
    document_id: str | None = None


class InterviewPrepRequest(BaseModel):
    job_id: str


class InterviewQuestion(BaseModel):
    category: str   # behavioral|technical|project|company
    question: str
    guidance: str


class InterviewPrep(BaseModel):
    job_id: str
    questions: list[InterviewQuestion]
