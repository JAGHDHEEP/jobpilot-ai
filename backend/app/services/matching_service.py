"""Orchestrate job matching: compute scores, generate rationale, persist."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.factory import get_llm, parse_json_response
from app.ai.matching import compute_match
from app.ai.prompts import MATCH_RATIONALE_SYSTEM, PROMPT_VERSION, match_rationale_user
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.job import Job, JobMatch
from app.models.profile import Profile
from app.services.ai_usage import record_usage
from app.services.feature_extraction import job_to_features, profile_to_features

log = get_logger()


async def _load_profile(db: AsyncSession, user_id: str) -> Profile:
    stmt = (
        select(Profile)
        .where(Profile.user_id == user_id)
        .options(
            selectinload(Profile.skills),
            selectinload(Profile.projects),
            selectinload(Profile.experiences),
            selectinload(Profile.educations),
        )
    )
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if not profile:
        raise NotFoundError("Profile not found. Complete your profile first.")
    return profile


async def match_job(db: AsyncSession, user_id: str, job: Job,
                    with_rationale: bool = True) -> JobMatch:
    profile = await _load_profile(db, user_id)
    pf = profile_to_features(profile)
    jf = job_to_features(job)
    result = compute_match(pf, jf)

    rationale = None
    if with_rationale:
        try:
            llm = get_llm()
            resp = await llm.complete(
                system=MATCH_RATIONALE_SYSTEM,
                user=match_rationale_user(result.scores_dict, result.missing_skills,
                                          result.missing_keywords, job.title, job.company),
                json_mode=True, temperature=0.3, max_tokens=400,
            )
            rationale = parse_json_response(resp).get("rationale")
            await record_usage(db, user_id=user_id, operation="match", resp=resp)
        except Exception as exc:  # pragma: no cover
            log.warning("rationale_failed", error=str(exc))

    existing = (await db.execute(
        select(JobMatch).where(JobMatch.user_id == user_id, JobMatch.job_id == job.id)
    )).scalar_one_or_none()

    fields = dict(
        overall_score=result.overall,
        skill_score=result.components["skill"].score,
        project_score=result.components["project"].score,
        experience_score=result.components["experience"].score,
        education_score=result.components["education"].score,
        keyword_score=result.components["keyword"].score,
        missing_skills=result.missing_skills,
        missing_keywords=result.missing_keywords,
        rationale=rationale,
        model_version=PROMPT_VERSION,
    )
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        match = existing
    else:
        match = JobMatch(user_id=user_id, job_id=job.id,
                         created_at=datetime.now(timezone.utc), **fields)
        db.add(match)
    await db.flush()
    return match


async def match_user_against_jobs(db: AsyncSession, user_id: str,
                                  jobs: list[Job]) -> list[JobMatch]:
    """Batch scoring without per-job rationale (cheaper); used by recommender."""
    profile = await _load_profile(db, user_id)
    pf = profile_to_features(profile)
    matches: list[JobMatch] = []
    for job in jobs:
        result = compute_match(pf, job_to_features(job))
        existing = (await db.execute(
            select(JobMatch).where(JobMatch.user_id == user_id, JobMatch.job_id == job.id)
        )).scalar_one_or_none()
        fields = dict(
            overall_score=result.overall,
            skill_score=result.components["skill"].score,
            project_score=result.components["project"].score,
            experience_score=result.components["experience"].score,
            education_score=result.components["education"].score,
            keyword_score=result.components["keyword"].score,
            missing_skills=result.missing_skills,
            missing_keywords=result.missing_keywords,
            model_version=PROMPT_VERSION,
        )
        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
            matches.append(existing)
        else:
            m = JobMatch(user_id=user_id, job_id=job.id,
                         created_at=datetime.now(timezone.utc), **fields)
            db.add(m)
            matches.append(m)
    await db.flush()
    return matches
