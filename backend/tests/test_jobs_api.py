"""Integration tests for jobs, matching, profile, applications."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio

_JOB = {
    "title": "Senior Backend Engineer",
    "company": "Acme",
    "description": "Build APIs with Python and FastAPI. Docker and AWS required. 3+ years.",
    "requirements": ["Python", "FastAPI", "Docker", "AWS"],
    "keywords": ["python", "fastapi", "docker", "aws"],
    "experience_min": 3,
}


async def _add_skills(client, skills):
    for s in skills:
        r = await client.post("/api/v1/profile/skills", json={"name": s})
        assert r.status_code == 201


async def test_create_and_search_job(auth_client):
    r = await auth_client.post("/api/v1/jobs", json=_JOB)
    assert r.status_code == 201
    job_id = r.json()["id"]

    r = await auth_client.get("/api/v1/jobs", params={"q": "Backend"})
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    assert any(item["id"] == job_id for item in r.json()["items"])


async def test_match_job_produces_explainable_score(auth_client):
    await _add_skills(auth_client, ["Python", "FastAPI", "Docker", "AWS"])
    job_id = (await auth_client.post("/api/v1/jobs", json=_JOB)).json()["id"]

    r = await auth_client.post(f"/api/v1/jobs/{job_id}/match")
    assert r.status_code == 200
    match = r.json()
    assert 0 <= match["overall_score"] <= 100
    assert match["skill_score"] == 100              # all required skills present
    assert match["rationale"]                        # mock LLM provides rationale
    assert match["missing_skills"] == []


async def test_match_reports_missing_skills(auth_client):
    await _add_skills(auth_client, ["Python"])
    job_id = (await auth_client.post("/api/v1/jobs", json=_JOB)).json()["id"]
    match = (await auth_client.post(f"/api/v1/jobs/{job_id}/match")).json()
    assert "aws" in [m.lower() for m in match["missing_skills"]]


async def test_application_tracker_and_analytics(auth_client):
    job_id = (await auth_client.post("/api/v1/jobs", json=_JOB)).json()["id"]
    r = await auth_client.post("/api/v1/applications",
                               json={"job_id": job_id, "status": "applied"})
    assert r.status_code == 201
    app_id = r.json()["id"]

    r = await auth_client.patch(f"/api/v1/applications/{app_id}/status",
                                json={"status": "interview", "note": "Phone screen"})
    assert r.status_code == 200
    assert r.json()["status"] == "interview"
    assert len(r.json()["events"]) >= 2

    analytics = (await auth_client.get("/api/v1/applications/analytics")).json()
    assert analytics["total"] == 1
    assert analytics["interview_rate"] == 1.0


async def test_recommendations_build_and_fetch(auth_client):
    await _add_skills(auth_client, ["Python", "FastAPI"])
    await auth_client.post("/api/v1/jobs", json=_JOB)
    assert (await auth_client.post("/api/v1/jobs/recommendations/build")).status_code == 200
    recs = (await auth_client.get("/api/v1/jobs/recommendations/today")).json()
    assert isinstance(recs, list)
    assert len(recs) >= 1
    assert recs[0]["rank"] == 1
