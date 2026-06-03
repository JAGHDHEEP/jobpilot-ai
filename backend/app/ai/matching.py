"""Deterministic, explainable job-matching engine.

The numeric score is computed deterministically from structured data so it is
reproducible and auditable. The LLM only produces a natural-language rationale that
explains (never overrides) the computed numbers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

WEIGHTS = {
    "skill": 0.30,
    "project": 0.25,
    "experience": 0.20,
    "education": 0.10,
    "keyword": 0.15,
}

_DEGREE_RANK = {
    "phd": 5, "doctor": 5, "master": 4, "mba": 4, "bachelor": 3, "btech": 3, "be": 3,
    "associate": 2, "diploma": 2, "high school": 1,
}

_STOPWORDS = {
    "and", "or", "the", "a", "an", "to", "of", "in", "with", "for", "on", "as", "is", "are",
    "we", "you", "our", "your", "will", "be", "have", "has", "experience", "years", "year",
    "work", "team", "role", "job", "ability", "strong", "good", "etc", "including",
}


def normalize(token: str) -> str:
    return re.sub(r"[^a-z0-9+#.]", "", token.lower()).strip()


def tokenize(text: str) -> list[str]:
    return [normalize(t) for t in re.findall(r"[A-Za-z0-9+#.]+", text or "")]


def keyword_set(text: str, min_len: int = 2) -> set[str]:
    return {t for t in tokenize(text) if len(t) >= min_len and t not in _STOPWORDS}


@dataclass
class ProfileFeatures:
    skills: set[str]
    project_text: str
    experience_years: float
    titles: list[str]
    degree_rank: int
    all_text: str


@dataclass
class JobFeatures:
    skills: set[str]            # explicit requirement skills
    keywords: set[str]          # full JD keyword set
    title: str
    experience_min: float
    degree_rank: int
    text: str


@dataclass
class ComponentResult:
    score: int                  # 0..100
    evidence: str
    missing: list[str] = field(default_factory=list)


@dataclass
class MatchResult:
    overall: int
    components: dict[str, ComponentResult]
    missing_skills: list[str]
    missing_keywords: list[str]

    @property
    def scores_dict(self) -> dict[str, int]:
        return {
            "overall_score": self.overall,
            "skill_score": self.components["skill"].score,
            "project_score": self.components["project"].score,
            "experience_score": self.components["experience"].score,
            "education_score": self.components["education"].score,
            "keyword_score": self.components["keyword"].score,
        }


def _degree_rank_from_text(text: str) -> int:
    low = (text or "").lower()
    best = 0
    for key, rank in _DEGREE_RANK.items():
        if key in low:
            best = max(best, rank)
    return best


def score_skills(profile: ProfileFeatures, job: JobFeatures) -> ComponentResult:
    required = job.skills or job.keywords
    if not required:
        return ComponentResult(70, "No explicit skill requirements detected.")
    matched = profile.skills & required
    missing = sorted(required - profile.skills)
    coverage = len(matched) / len(required)
    score = round(coverage * 100)
    return ComponentResult(
        score=score,
        evidence=f"Matched {len(matched)}/{len(required)} required skills.",
        missing=missing[:25],
    )


def score_projects(profile: ProfileFeatures, job: JobFeatures) -> ComponentResult:
    if not profile.project_text.strip():
        return ComponentResult(40, "No projects on profile to evaluate relevance.")
    proj_tokens = keyword_set(profile.project_text)
    overlap = proj_tokens & job.keywords
    denom = max(len(job.keywords), 1)
    score = min(100, round(len(overlap) / denom * 100 * 1.5))  # projects weighted generously
    return ComponentResult(score, f"{len(overlap)} job keywords appear in projects.")


def score_experience(profile: ProfileFeatures, job: JobFeatures) -> ComponentResult:
    req = job.experience_min or 0
    if req <= 0:
        years_score = 80
    else:
        years_score = min(100, round(profile.experience_years / req * 100))
    # title relevance
    title_tokens = keyword_set(job.title)
    prof_title_tokens = keyword_set(" ".join(profile.titles))
    title_overlap = (title_tokens & prof_title_tokens)
    title_bonus = min(20, len(title_overlap) * 7)
    score = min(100, round(0.8 * years_score + title_bonus))
    return ComponentResult(
        score,
        f"{profile.experience_years:.1f}y experience vs {req:.0f}y required; "
        f"title overlap: {', '.join(sorted(title_overlap)) or 'none'}.",
    )


def score_education(profile: ProfileFeatures, job: JobFeatures) -> ComponentResult:
    if job.degree_rank == 0:
        return ComponentResult(80, "No specific degree requirement detected.")
    if profile.degree_rank >= job.degree_rank:
        return ComponentResult(100, "Meets or exceeds the required degree level.")
    gap = job.degree_rank - profile.degree_rank
    return ComponentResult(max(0, 100 - gap * 30), "Below the required degree level.")


def score_keywords(profile: ProfileFeatures, job: JobFeatures) -> ComponentResult:
    if not job.keywords:
        return ComponentResult(70, "No keywords extracted from JD.")
    prof_tokens = keyword_set(profile.all_text)
    matched = prof_tokens & job.keywords
    missing = sorted(job.keywords - prof_tokens)
    score = round(len(matched) / len(job.keywords) * 100)
    return ComponentResult(score, f"ATS keyword coverage {score}%.", missing[:25])


def compute_match(profile: ProfileFeatures, job: JobFeatures) -> MatchResult:
    components = {
        "skill": score_skills(profile, job),
        "project": score_projects(profile, job),
        "experience": score_experience(profile, job),
        "education": score_education(profile, job),
        "keyword": score_keywords(profile, job),
    }
    overall = round(sum(components[k].score * WEIGHTS[k] for k in WEIGHTS))
    return MatchResult(
        overall=overall,
        components=components,
        missing_skills=components["skill"].missing,
        missing_keywords=components["keyword"].missing,
    )
