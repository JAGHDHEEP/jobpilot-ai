"""Concrete source adapters.

Real third-party APIs (LinkedIn, Naukri, Indeed, Foundit, Wellfound, Glassdoor) require
authenticated partner access or compliant scraping. Each adapter below conforms to the
same `JobConnector` interface; production credentials/endpoints plug in via env settings.

`SampleConnector` is fully functional offline and seeds realistic demo jobs so the rest
of the system (matching, recommendations, optimization) is exercisable end-to-end.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app.connectors.base import JobConnector, register
from app.connectors.rss import RSSConnector
from app.models.enums import EmploymentType, JobSource, RemoteType
from app.schemas.job import JobCreate

_TITLES = [
    "Senior Backend Engineer", "Full Stack Developer", "Machine Learning Engineer",
    "Data Engineer", "DevOps Engineer", "Platform Engineer", "AI Engineer",
    "Software Engineer II", "Cloud Infrastructure Engineer",
]
_COMPANIES = ["Acme Corp", "Nimbus AI", "DataForge", "CloudScale", "Quantum Labs", "Hyperion"]
_SKILLS_POOL = [
    "Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "AWS", "React", "TypeScript",
    "Redis", "Celery", "CI/CD", "Terraform", "GraphQL", "Kafka", "PyTorch", "Next.js",
]


class SampleConnector(JobConnector):
    """Deterministic-ish demo source for development and tests."""

    source = JobSource.manual
    mechanism = "api"

    async def fetch(self, *, query="", location="Remote", limit=20) -> list[JobCreate]:
        rng = random.Random(42)
        out: list[JobCreate] = []
        for i in range(min(limit, 20)):
            title = rng.choice(_TITLES)
            skills = rng.sample(_SKILLS_POOL, k=6)
            exp = rng.choice([1, 2, 3, 5])
            out.append(JobCreate(
                source=self.source,
                source_job_id=f"sample-{i}",
                title=title,
                company=rng.choice(_COMPANIES),
                location=location or "Remote",
                remote_type=rng.choice(list(RemoteType)),
                employment_type=EmploymentType.full_time,
                salary_min=80_000 + i * 2_000,
                salary_max=140_000 + i * 3_000,
                currency="USD",
                description=(
                    f"We are hiring a {title}. You will build scalable systems. "
                    f"Required skills: {', '.join(skills)}. "
                    f"{exp}+ years experience. Bachelor's degree preferred."
                ),
                requirements=skills,
                keywords=skills,
                experience_min=exp,
                experience_max=exp + 3,
                posted_at=datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 10)),
                apply_url="https://example.com/apply",
                company_rating=round(rng.uniform(3.5, 4.9), 1),
            ))
        return out


# --- API-backed adapters (interface-complete; require credentials to return live data) ---
class _CredentialedAPIConnector(JobConnector):
    mechanism = "api"
    enabled = False  # enabled once API credentials are configured

    async def fetch(self, *, query="", location="", limit=50) -> list[JobCreate]:
        # Plug in the partner SDK / REST call here, then map responses -> JobCreate.
        # Returns empty until credentials/endpoint are wired via settings.
        return []


class LinkedInConnector(_CredentialedAPIConnector):
    source = JobSource.linkedin


class IndeedConnector(_CredentialedAPIConnector):
    source = JobSource.indeed


class NaukriConnector(_CredentialedAPIConnector):
    source = JobSource.naukri


class FounditConnector(_CredentialedAPIConnector):
    source = JobSource.foundit


class WellfoundConnector(_CredentialedAPIConnector):
    source = JobSource.wellfound


class GlassdoorConnector(_CredentialedAPIConnector):
    source = JobSource.glassdoor


def register_all() -> None:
    register(SampleConnector())
    register(LinkedInConnector())
    register(IndeedConnector())
    register(NaukriConnector())
    register(FounditConnector())
    register(WellfoundConnector())
    register(GlassdoorConnector())
    # Example: a company career page exposed via RSS
    register(RSSConnector(source=JobSource.company))


register_all()
