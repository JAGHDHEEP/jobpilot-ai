"""Unit tests for the deterministic matching engine."""
from __future__ import annotations

from app.ai.matching import (
    JobFeatures,
    ProfileFeatures,
    compute_match,
    keyword_set,
    normalize,
)


def _profile(skills, project_text="", years=3.0, titles=None, degree=3, all_text=""):
    return ProfileFeatures(
        skills=set(skills), project_text=project_text, experience_years=years,
        titles=titles or [], degree_rank=degree, all_text=all_text or " ".join(skills),
    )


def _job(skills, keywords=None, title="Engineer", exp=2, degree=3, text=""):
    return JobFeatures(
        skills=set(skills), keywords=set(keywords or skills), title=title,
        experience_min=exp, degree_rank=degree, text=text,
    )


def test_normalize_and_tokenize():
    assert normalize("C++") == "c++"
    assert "python" in keyword_set("I love Python and SQL")


def test_perfect_skill_match_scores_high():
    p = _profile(["python", "fastapi", "docker"], project_text="built python fastapi api docker")
    j = _job(["python", "fastapi", "docker"], title="Backend Engineer")
    result = compute_match(p, j)
    assert result.components["skill"].score == 100
    assert result.overall >= 70
    assert result.missing_skills == []


def test_missing_skills_are_reported():
    p = _profile(["python"])
    j = _job(["python", "kubernetes", "aws"])
    result = compute_match(p, j)
    assert set(result.missing_skills) >= {"kubernetes", "aws"}
    assert result.components["skill"].score < 100


def test_overall_is_weighted_blend_0_100():
    p = _profile(["python"], years=1, degree=1)
    j = _job(["python", "go", "rust"], exp=10, degree=5)
    result = compute_match(p, j)
    assert 0 <= result.overall <= 100
    for key in ("skill", "project", "experience", "education", "keyword"):
        assert 0 <= result.components[key].score <= 100


def test_experience_below_requirement_lowers_score():
    junior = compute_match(_profile(["python"], years=1), _job(["python"], exp=10))
    senior = compute_match(_profile(["python"], years=12), _job(["python"], exp=10))
    assert senior.components["experience"].score >= junior.components["experience"].score
