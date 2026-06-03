"""Tests for AI generation tools and resume parsing (mock provider)."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio

_JOB = {
    "title": "ML Engineer", "company": "Nimbus",
    "description": "Build ML systems with Python, PyTorch, and AWS.",
    "requirements": ["Python", "PyTorch", "AWS"], "keywords": ["python", "pytorch", "aws"],
    "experience_min": 2,
}


async def test_optimize_resume_returns_markdown(auth_client, db):
    # seed a master resume document directly
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.models.document import Document
    from app.models.enums import DocKind
    from app.models.user import User

    user = (await db.execute(select(User).where(User.email == "user@test.com"))).scalar_one()
    db.add(Document(user_id=user.id, kind=DocKind.resume, title="master", is_master=True,
                    parsed_text="Python engineer with FastAPI and AWS experience.",
                    created_at=datetime.now(timezone.utc)))
    await db.commit()

    job_id = (await auth_client.post("/api/v1/jobs", json=_JOB)).json()["id"]
    r = await auth_client.post("/api/v1/ai/optimize-resume", json={"job_id": job_id})
    assert r.status_code == 200
    assert r.json()["markdown"]
    assert r.json()["document_id"]


async def test_cover_letter_and_interview_prep(auth_client):
    job_id = (await auth_client.post("/api/v1/jobs", json=_JOB)).json()["id"]

    r = await auth_client.post("/api/v1/ai/cover-letter", json={"job_id": job_id})
    assert r.status_code == 200
    assert r.json()["body"]

    r = await auth_client.post("/api/v1/ai/interview-prep", json={"job_id": job_id})
    assert r.status_code == 200
    qs = r.json()["questions"]
    assert len(qs) >= 1
    assert {"category", "question", "guidance"} <= set(qs[0].keys())


@pytest.mark.filterwarnings("ignore")
async def test_resume_text_extraction_heuristics():
    from app.services.resume_parser import heuristic_skills
    skills = heuristic_skills("Experienced in Python, FastAPI, Docker and Kubernetes on AWS.")
    assert {"python", "fastapi", "docker", "kubernetes", "aws"} <= set(skills)
