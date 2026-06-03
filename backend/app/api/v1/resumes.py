"""Resume / document upload, parsing, listing, review."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, UploadFile, status
from sqlalchemy import select

from app.ai.rag import index_profile
from app.api.deps import CurrentUser, DBSession
from app.core.config import settings
from app.core.exceptions import AppError, NotFoundError
from app.models.document import Document
from app.models.enums import DocKind
from app.schemas.common import Message
from app.schemas.document import DocumentOut, ParsedProfile, ResumeReview
from app.services import generation, profile_service
from app.services.resume_parser import parse_resume

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _validate_upload(file: UploadFile, content: bytes) -> None:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise AppError(f"File type {ext or '?'} not allowed.", code="bad_file_type")
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise AppError("File exceeds maximum allowed size.", code="file_too_large",
                       status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    if not content:
        raise AppError("Empty file.", code="empty_file")


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(...),
    is_master: bool = Form(True),
    import_to_profile: bool = Form(True),
) -> DocumentOut:
    content = await file.read()
    _validate_upload(file, content)

    raw_text, parsed = await parse_resume(file.filename or "resume", content)

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    storage_key = f"{user.id}/{uuid.uuid4().hex}_{os.path.basename(file.filename or 'resume')}"
    path = os.path.join(settings.UPLOAD_DIR, storage_key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(content)

    if is_master:
        for d in (await db.execute(
            select(Document).where(Document.user_id == user.id,
                                   Document.kind == DocKind.resume,
                                   Document.is_master.is_(True)))).scalars().all():
            d.is_master = False

    doc = Document(
        user_id=user.id, kind=DocKind.resume, title=file.filename or "Resume",
        storage_key=storage_key, mime_type=file.content_type, size_bytes=len(content),
        is_master=is_master, parsed_text=raw_text, structured=parsed.model_dump(),
        created_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    await db.flush()

    if import_to_profile:
        await profile_service.import_parsed(db, str(user.id), parsed)
    await index_profile(str(user.id), parsed)
    await db.commit()
    return DocumentOut.model_validate(doc, from_attributes=True)


@router.get("", response_model=list[DocumentOut])
async def list_documents(user: CurrentUser, db: DBSession,
                         kind: DocKind | None = None) -> list[DocumentOut]:
    stmt = select(Document).where(Document.user_id == user.id)
    if kind:
        stmt = stmt.where(Document.kind == kind)
    rows = (await db.execute(stmt.order_by(Document.created_at.desc()))).scalars().all()
    return [DocumentOut.model_validate(r, from_attributes=True) for r in rows]


@router.get("/{doc_id}/parsed", response_model=ParsedProfile)
async def get_parsed(doc_id: str, user: CurrentUser, db: DBSession) -> ParsedProfile:
    doc = (await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user.id)
    )).scalar_one_or_none()
    if not doc or not doc.structured:
        raise NotFoundError("Parsed resume not found.")
    return ParsedProfile.model_validate(doc.structured)


@router.post("/{doc_id}/review", response_model=ResumeReview)
async def review(doc_id: str, user: CurrentUser, db: DBSession) -> ResumeReview:
    doc = (await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user.id)
    )).scalar_one_or_none()
    if not doc:
        raise NotFoundError("Resume not found.")
    result = await generation.review_resume(db, str(user.id), doc.parsed_text or "")
    await db.commit()
    return result


@router.delete("/{doc_id}", response_model=Message)
async def delete_document(doc_id: str, user: CurrentUser, db: DBSession) -> Message:
    doc = (await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user.id)
    )).scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document not found.")
    await db.delete(doc)
    await db.commit()
    return Message(message="Document deleted.")
