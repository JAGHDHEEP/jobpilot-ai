"""Profile aggregate loading + child-collection CRUD + import from parsed resume."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.profile import (
    Achievement,
    Certification,
    Education,
    Experience,
    Profile,
    Project,
    Skill,
)
from app.schemas.document import ParsedProfile
from app.schemas.profile import ProfileUpdate

_CHILD_MODELS = {
    "education": Education,
    "experience": Experience,
    "project": Project,
    "skill": Skill,
    "certification": Certification,
    "achievement": Achievement,
}


async def get_profile(db: AsyncSession, user_id: str) -> Profile:
    stmt = (
        select(Profile)
        .where(Profile.user_id == user_id)
        .options(
            selectinload(Profile.educations),
            selectinload(Profile.experiences),
            selectinload(Profile.projects),
            selectinload(Profile.skills),
            selectinload(Profile.certifications),
            selectinload(Profile.achievements),
        )
    )
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user_id)
        db.add(profile)
        await db.flush()
        await db.refresh(profile)
    return profile


async def update_profile(db: AsyncSession, user_id: str, data: ProfileUpdate) -> Profile:
    profile = await get_profile(db, user_id)
    payload = data.model_dump(exclude_unset=True)
    if "languages" in payload and payload["languages"] is not None:
        payload["languages"] = [lang.model_dump() if hasattr(lang, "model_dump") else lang
                                for lang in payload["languages"]]
    for k, v in payload.items():
        setattr(profile, k, v)
    await db.flush()
    return profile


async def add_child(db: AsyncSession, user_id: str, kind: str, data: dict):
    model = _CHILD_MODELS[kind]
    profile = await get_profile(db, user_id)
    obj = model(profile_id=profile.id, **data)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_child(db: AsyncSession, user_id: str, kind: str, child_id: str) -> None:
    model = _CHILD_MODELS[kind]
    profile = await get_profile(db, user_id)
    obj = (await db.execute(
        select(model).where(model.id == child_id, model.profile_id == profile.id)
    )).scalar_one_or_none()
    if not obj:
        raise NotFoundError(f"{kind} not found.")
    await db.delete(obj)
    await db.flush()


async def import_parsed(db: AsyncSession, user_id: str, parsed: ParsedProfile) -> Profile:
    """Merge a parsed resume into the profile (adds skills/experience/projects)."""
    profile = await get_profile(db, user_id)
    if parsed.summary and not profile.summary:
        profile.summary = parsed.summary

    existing_skills = {s.name.lower() for s in profile.skills}
    for name in parsed.skills:
        if name.lower() not in existing_skills:
            db.add(Skill(profile_id=profile.id, name=name))
            existing_skills.add(name.lower())

    for exp in parsed.experiences:
        if exp.get("company") and exp.get("role"):
            db.add(Experience(
                profile_id=profile.id, company=exp["company"], role=exp["role"],
                description=exp.get("description"), highlights=exp.get("highlights", []),
            ))
    for proj in parsed.projects:
        if proj.get("title"):
            db.add(Project(
                profile_id=profile.id, title=proj["title"],
                description=proj.get("description"),
                technologies=proj.get("technologies", []),
            ))
    for ed in parsed.educations:
        if ed.get("degree") and ed.get("institution"):
            db.add(Education(
                profile_id=profile.id, degree=ed["degree"], institution=ed["institution"],
                graduation_year=ed.get("year"),
            ))
    await db.flush()
    return await get_profile(db, user_id)
