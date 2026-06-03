"""AI generation services: resume optimization, cover letter, interview prep, review."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_llm, parse_json_response
from app.ai.prompts import (
    COVER_LETTER_SYSTEM,
    INTERVIEW_SYSTEM,
    OPTIMIZE_SYSTEM,
    RESUME_REVIEW_SYSTEM,
)
from app.ai.rag import retrieve_profile_context
from app.core.exceptions import NotFoundError
from app.models.document import Document
from app.models.enums import DocKind
from app.models.job import Job
from app.schemas.document import (
    CoverLetter,
    InterviewPrep,
    InterviewQuestion,
    OptimizedResume,
    ResumeReview,
    ResumeReviewSection,
)
from app.services.ai_usage import record_usage


async def _get_job(db: AsyncSession, job_id: str) -> Job:
    job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if not job:
        raise NotFoundError("Job not found.")
    return job


async def _master_text(db: AsyncSession, user_id: str, doc_id: str | None) -> str:
    stmt = select(Document).where(Document.user_id == user_id, Document.kind == DocKind.resume)
    stmt = stmt.where(Document.id == doc_id) if doc_id else stmt.where(Document.is_master.is_(True))
    doc = (await db.execute(stmt.limit(1))).scalar_one_or_none()
    if not doc:
        raise NotFoundError("Master resume not found. Upload a resume first.")
    return doc.parsed_text or ""


async def optimize_resume(db: AsyncSession, user_id: str, job_id: str,
                          master_doc_id: str | None = None) -> OptimizedResume:
    job = await _get_job(db, job_id)
    master = await _master_text(db, user_id, master_doc_id)
    context = await retrieve_profile_context(user_id, job.description) or master[:4000]
    user_msg = (
        f"# Job: {job.title} at {job.company}\n{job.description}\n\n"
        f"# Candidate profile context (grounded, truthful):\n{context}\n\n"
        f"# Existing master resume text:\n{master[:4000]}\n\n"
        "Produce the tailored resume now."
    )
    llm = get_llm()
    resp = await llm.complete(system=OPTIMIZE_SYSTEM, user=user_msg, json_mode=True,
                              temperature=0.3, max_tokens=2500)
    await record_usage(db, user_id=user_id, operation="optimize", resp=resp)
    data = parse_json_response(resp)
    return OptimizedResume(
        job_id=job_id,
        markdown=data.get("markdown") or master,
        added_keywords=data.get("added_keywords") or [],
    )


async def generate_cover_letter(db: AsyncSession, user_id: str, job_id: str,
                                tone: str = "professional") -> CoverLetter:
    job = await _get_job(db, job_id)
    context = await retrieve_profile_context(user_id, job.description)
    llm = get_llm()
    resp = await llm.complete(
        system=COVER_LETTER_SYSTEM.format(tone=tone),
        user=f"# Job: {job.title} at {job.company}\n{job.description}\n\n"
             f"# Candidate context:\n{context}",
        json_mode=True, temperature=0.5, max_tokens=900,
    )
    await record_usage(db, user_id=user_id, operation="cover", resp=resp)
    data = parse_json_response(resp)
    return CoverLetter(job_id=job_id, body=data.get("body") or resp.text)


async def generate_interview_prep(db: AsyncSession, user_id: str, job_id: str) -> InterviewPrep:
    job = await _get_job(db, job_id)
    context = await retrieve_profile_context(user_id, job.description)
    llm = get_llm()
    resp = await llm.complete(
        system=INTERVIEW_SYSTEM,
        user=f"# Job: {job.title} at {job.company}\n{job.description}\n\n# Candidate:\n{context}",
        json_mode=True, temperature=0.6, max_tokens=1500,
    )
    await record_usage(db, user_id=user_id, operation="interview", resp=resp)
    data = parse_json_response(resp)
    questions = [
        InterviewQuestion(category=q.get("category", "general"),
                          question=q.get("question", ""),
                          guidance=q.get("guidance", ""))
        for q in data.get("questions", [])
    ]
    return InterviewPrep(job_id=job_id, questions=questions)


async def review_resume(db: AsyncSession, user_id: str, resume_text: str) -> ResumeReview:
    llm = get_llm()
    resp = await llm.complete(system=RESUME_REVIEW_SYSTEM, user=resume_text[:8000],
                              json_mode=True, temperature=0.2, max_tokens=1200)
    await record_usage(db, user_id=user_id, operation="review", resp=resp)
    d = parse_json_response(resp)
    sections = [ResumeReviewSection(**s) for s in d.get("sections", [])]
    return ResumeReview(
        ats_score=d.get("ats_score", 0),
        formatting_score=d.get("formatting_score", 0),
        keyword_score=d.get("keyword_score", 0),
        impact_score=d.get("impact_score", 0),
        project_quality_score=d.get("project_quality_score", 0),
        skill_relevance_score=d.get("skill_relevance_score", 0),
        sections=sections,
        suggestions=d.get("suggestions", []),
    )
