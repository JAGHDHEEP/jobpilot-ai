"""Build matching feature objects from ORM profile + job rows."""
from __future__ import annotations

from datetime import date

from app.ai.matching import (
    JobFeatures,
    ProfileFeatures,
    _degree_rank_from_text,
    keyword_set,
    normalize,
)
from app.models.job import Job
from app.models.profile import Profile


def _years_of_experience(profile: Profile) -> float:
    total_months = 0
    for exp in profile.experiences:
        start = exp.start_date or date.today()
        end = exp.end_date or date.today()
        total_months += max(0, (end.year - start.year) * 12 + (end.month - start.month))
    return round(total_months / 12, 1)


def _max_degree_rank(profile: Profile) -> int:
    best = 0
    for ed in profile.educations:
        best = max(best, _degree_rank_from_text(f"{ed.degree} {ed.field_of_study or ''}"))
    return best


def profile_to_features(profile: Profile) -> ProfileFeatures:
    skills = {normalize(s.name) for s in profile.skills if s.name}
    project_text = " ".join(
        f"{p.title} {p.description or ''} {' '.join(p.technologies or [])} "
        f"{' '.join(p.achievements or [])}"
        for p in profile.projects
    )
    titles = [e.role for e in profile.experiences if e.role]
    all_text = " ".join([
        profile.summary or "",
        " ".join(s.name for s in profile.skills),
        project_text,
        " ".join(f"{e.role} {e.company} {e.description or ''}" for e in profile.experiences),
        " ".join(f"{ed.degree} {ed.institution}" for ed in profile.educations),
    ])
    return ProfileFeatures(
        skills=skills,
        project_text=project_text,
        experience_years=_years_of_experience(profile),
        titles=titles,
        degree_rank=_max_degree_rank(profile),
        all_text=all_text,
    )


def job_to_features(job: Job) -> JobFeatures:
    req_text = " ".join(job.requirements or [])
    skills = {normalize(s) for s in (job.keywords or [])} or keyword_set(req_text)
    keywords = keyword_set(f"{job.title} {job.description} {req_text}")
    return JobFeatures(
        skills=skills,
        keywords=keywords,
        title=job.title,
        experience_min=float(job.experience_min or 0),
        degree_rank=_degree_rank_from_text(job.description + " " + req_text),
        text=f"{job.title} {job.description} {req_text}",
    )
