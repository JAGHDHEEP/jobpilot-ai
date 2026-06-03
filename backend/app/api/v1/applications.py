"""Application tracker routes + analytics."""
from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.application import (
    ApplicationAnalytics,
    ApplicationCreate,
    ApplicationOut,
    ApplicationStatusUpdate,
)
from app.services import application_service

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def create(body: ApplicationCreate, user: CurrentUser, db: DBSession) -> ApplicationOut:
    app = await application_service.create_application(
        db, str(user.id), body.job_id, body.status,
        resume_doc_id=body.resume_doc_id, cover_doc_id=body.cover_doc_id, notes=body.notes,
    )
    await db.commit()
    return ApplicationOut.model_validate(app, from_attributes=True)


@router.get("", response_model=list[ApplicationOut])
async def list_all(user: CurrentUser, db: DBSession) -> list[ApplicationOut]:
    apps = await application_service.list_applications(db, str(user.id))
    return [ApplicationOut.model_validate(a, from_attributes=True) for a in apps]


@router.patch("/{app_id}/status", response_model=ApplicationOut)
async def update_status(app_id: str, body: ApplicationStatusUpdate,
                        user: CurrentUser, db: DBSession) -> ApplicationOut:
    app = await application_service.update_status(db, str(user.id), app_id, body.status, body.note)
    await db.commit()
    return ApplicationOut.model_validate(app, from_attributes=True)


@router.get("/analytics", response_model=ApplicationAnalytics)
async def get_analytics(user: CurrentUser, db: DBSession) -> ApplicationAnalytics:
    return await application_service.analytics(db, str(user.id))
