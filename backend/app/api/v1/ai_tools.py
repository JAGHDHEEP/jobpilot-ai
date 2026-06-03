"""AI generation routes: optimize resume, cover letter, interview prep."""
from __future__ import annotations

import io
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, DBSession
from app.models.document import Document
from app.models.enums import DocKind
from app.schemas.document import (
    CoverLetter,
    CoverLetterRequest,
    InterviewPrep,
    InterviewPrepRequest,
    OptimizeRequest,
    OptimizedResume,
)
from app.services import generation
from app.services.pdf import markdown_to_pdf

router = APIRouter(prefix="/ai", tags=["ai-tools"])


@router.post("/optimize-resume", response_model=OptimizedResume)
async def optimize(body: OptimizeRequest, user: CurrentUser, db: DBSession) -> OptimizedResume:
    result = await generation.optimize_resume(db, str(user.id), body.job_id, body.master_doc_id)
    doc = Document(
        user_id=user.id, kind=DocKind.resume, title=f"Tailored resume — {body.job_id[:8]}",
        is_master=False, parsed_text=result.markdown, job_id=body.job_id,
        mime_type="text/markdown", created_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    await db.flush()
    result.document_id = str(doc.id)
    await db.commit()
    return result


@router.post("/optimize-resume/pdf")
async def optimize_pdf(body: OptimizeRequest, user: CurrentUser, db: DBSession):
    result = await generation.optimize_resume(db, str(user.id), body.job_id, body.master_doc_id)
    await db.commit()
    pdf = markdown_to_pdf(result.markdown, title="Tailored Resume")
    return StreamingResponse(
        io.BytesIO(pdf), media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=tailored_resume.pdf"},
    )


@router.post("/cover-letter", response_model=CoverLetter)
async def cover_letter(body: CoverLetterRequest, user: CurrentUser, db: DBSession) -> CoverLetter:
    result = await generation.generate_cover_letter(db, str(user.id), body.job_id, body.tone)
    doc = Document(
        user_id=user.id, kind=DocKind.cover_letter,
        title=f"Cover letter — {body.job_id[:8]}", parsed_text=result.body,
        job_id=body.job_id, mime_type="text/plain", created_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    await db.flush()
    result.document_id = str(doc.id)
    await db.commit()
    return result


@router.post("/interview-prep", response_model=InterviewPrep)
async def interview_prep(body: InterviewPrepRequest, user: CurrentUser,
                         db: DBSession) -> InterviewPrep:
    result = await generation.generate_interview_prep(db, str(user.id), body.job_id)
    await db.commit()
    return result
