"""Career insights: skill gaps, market demand, trending skills."""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models.job import Job, JobMatch
from app.models.profile import Profile, Skill
from app.services.feature_extraction import job_to_features

router = APIRouter(prefix="/insights", tags=["insights"])


class SkillDemand(BaseModel):
    skill: str
    demand: int


class CareerInsights(BaseModel):
    trending_skills: list[SkillDemand]
    most_requested: list[SkillDemand]
    skill_gaps: list[str]
    recommendations: list[str]


@router.get("", response_model=CareerInsights)
async def insights(user: CurrentUser, db: DBSession,
                   sample: int = 300) -> CareerInsights:
    jobs = (await db.execute(select(Job).limit(sample))).scalars().all()
    counter: Counter[str] = Counter()
    for job in jobs:
        counter.update(job_to_features(job).keywords)

    profile = (await db.execute(
        select(Profile).where(Profile.user_id == user.id)
    )).scalar_one_or_none()
    my_skills: set[str] = set()
    if profile:
        my_skills = {s.name.lower() for s in (await db.execute(
            select(Skill).where(Skill.profile_id == profile.id))).scalars().all()}

    most_requested = [SkillDemand(skill=k, demand=v) for k, v in counter.most_common(20)]
    gaps = [k for k, _ in counter.most_common(40) if k not in my_skills][:12]

    # "trending" = highest demand among skills appearing in the user's matched jobs
    matched_job_ids = [m.job_id for m in (await db.execute(
        select(JobMatch).where(JobMatch.user_id == user.id)
        .order_by(JobMatch.overall_score.desc()).limit(50))).scalars().all()]
    trending_counter: Counter[str] = Counter()
    if matched_job_ids:
        for job in (await db.execute(select(Job).where(Job.id.in_(matched_job_ids)))).scalars():
            trending_counter.update(job_to_features(job).keywords)
    trending = [SkillDemand(skill=k, demand=v) for k, v in trending_counter.most_common(15)] \
        or most_requested[:10]

    recs = [f"Consider learning '{g}' — it appears in many target roles." for g in gaps[:5]]
    return CareerInsights(trending_skills=trending, most_requested=most_requested,
                          skill_gaps=gaps, recommendations=recs)
