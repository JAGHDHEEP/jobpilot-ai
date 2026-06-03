"""Profile + child-collection CRUD routes.

NOTE: this module intentionally does NOT use ``from __future__ import annotations``.
The dynamic ``_crud`` factory relies on the ``in_model`` parameter annotation being a
real class object (not a deferred string) so FastAPI can build the request body model.
"""
from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import Message
from app.schemas.profile import (
    AchievementIn,
    AchievementOut,
    CertificationIn,
    CertificationOut,
    EducationIn,
    EducationOut,
    ExperienceIn,
    ExperienceOut,
    ProfileOut,
    ProfileUpdate,
    ProjectIn,
    ProjectOut,
    SkillIn,
    SkillOut,
)
from app.services import profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
async def get_my_profile(user: CurrentUser, db: DBSession) -> ProfileOut:
    profile = await profile_service.get_profile(db, str(user.id))
    return ProfileOut.model_validate(profile, from_attributes=True)


@router.patch("", response_model=ProfileOut)
async def update_my_profile(body: ProfileUpdate, user: CurrentUser, db: DBSession) -> ProfileOut:
    profile = await profile_service.update_profile(db, str(user.id), body)
    await db.commit()
    profile = await profile_service.get_profile(db, str(user.id))
    return ProfileOut.model_validate(profile, from_attributes=True)


def _crud(kind: str, in_model, out_model):
    sub = APIRouter()

    @sub.post("", response_model=out_model, status_code=status.HTTP_201_CREATED)
    async def add(body: in_model, user: CurrentUser, db: DBSession):  # type: ignore
        obj = await profile_service.add_child(db, str(user.id), kind, body.model_dump())
        await db.commit()
        return out_model.model_validate(obj, from_attributes=True)

    @sub.delete("/{child_id}", response_model=Message)
    async def remove(child_id: str, user: CurrentUser, db: DBSession) -> Message:
        await profile_service.delete_child(db, str(user.id), kind, child_id)
        await db.commit()
        return Message(message=f"{kind} deleted.")

    return sub


router.include_router(_crud("education", EducationIn, EducationOut), prefix="/educations",
                      tags=["profile"])
router.include_router(_crud("experience", ExperienceIn, ExperienceOut), prefix="/experiences",
                      tags=["profile"])
router.include_router(_crud("project", ProjectIn, ProjectOut), prefix="/projects",
                      tags=["profile"])
router.include_router(_crud("skill", SkillIn, SkillOut), prefix="/skills", tags=["profile"])
router.include_router(_crud("certification", CertificationIn, CertificationOut),
                      prefix="/certifications", tags=["profile"])
router.include_router(_crud("achievement", AchievementIn, AchievementOut),
                      prefix="/achievements", tags=["profile"])
