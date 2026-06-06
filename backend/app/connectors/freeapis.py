"""Real, key-less job connectors backed by free public job APIs.

- Remotive  (https://remotive.com/api/remote-jobs) — curated remote jobs, supports search.
- Arbeitnow (https://www.arbeitnow.com/api/job-board-api) — open job board feed.

Both return genuine live listings and require no API key. Responses are normalized to
JobCreate so they flow through the same dedupe → embed → match pipeline as every other
source. (LinkedIn/Naukri/Indeed/etc. have no free API; their connectors remain stubs in
adapters.py and light up once partner credentials are supplied.)
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

from app.connectors.base import JobConnector
from app.core.logging import get_logger
from app.models.enums import EmploymentType, JobSource, RemoteType
from app.schemas.job import JobCreate

log = get_logger()
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _clean(html: str) -> str:
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", html or "")).strip()


def _emp_type(raw: str | None) -> EmploymentType | None:
    if not raw:
        return None
    r = raw.lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "full_time": EmploymentType.full_time, "fulltime": EmploymentType.full_time,
        "part_time": EmploymentType.part_time, "contract": EmploymentType.contract,
        "internship": EmploymentType.internship, "temporary": EmploymentType.temporary,
        "freelance": EmploymentType.contract,
    }
    return mapping.get(r)


class RemotiveConnector(JobConnector):
    source = JobSource.remotive
    mechanism = "api"
    enabled = True
    URL = "https://remotive.com/api/remote-jobs"

    async def fetch(self, *, query="", location="", limit=50) -> list[JobCreate]:
        params = {"limit": str(min(limit, 100))}
        if query:
            params["search"] = query
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                resp = await client.get(self.URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # pragma: no cover - network best-effort
            log.warning("remotive_fetch_failed", error=str(exc))
            return []

        out: list[JobCreate] = []
        for j in data.get("jobs", [])[:limit]:
            tags = [t for t in (j.get("tags") or []) if t][:25]
            out.append(JobCreate(
                source=JobSource.remotive,
                source_job_id=str(j.get("id")),
                title=j.get("title", "").strip() or "Untitled",
                company=(j.get("company_name") or "Unknown").strip(),
                location=j.get("candidate_required_location") or "Remote",
                remote_type=RemoteType.remote,
                employment_type=_emp_type(j.get("job_type")),
                description=_clean(j.get("description"))[:8000] or j.get("title", ""),
                requirements=tags,
                keywords=tags,
                apply_url=j.get("url"),
                posted_at=_parse_dt(j.get("publication_date")),
                currency="USD",
            ))
        log.info("remotive_fetched", count=len(out), query=query)
        return out


class ArbeitnowConnector(JobConnector):
    source = JobSource.arbeitnow
    mechanism = "api"
    enabled = True
    URL = "https://www.arbeitnow.com/api/job-board-api"

    async def fetch(self, *, query="", location="", limit=50) -> list[JobCreate]:
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                resp = await client.get(self.URL)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # pragma: no cover
            log.warning("arbeitnow_fetch_failed", error=str(exc))
            return []

        q = (query or "").lower()
        out: list[JobCreate] = []
        for j in data.get("data", []):
            title = (j.get("title") or "").strip()
            if q and q not in title.lower() and q not in " ".join(j.get("tags") or []).lower():
                continue
            tags = [t for t in (j.get("tags") or []) if t][:25]
            out.append(JobCreate(
                source=JobSource.arbeitnow,
                source_job_id=j.get("slug"),
                title=title or "Untitled",
                company=(j.get("company_name") or "Unknown").strip(),
                location=j.get("location") or ("Remote" if j.get("remote") else None),
                remote_type=RemoteType.remote if j.get("remote") else RemoteType.onsite,
                employment_type=_emp_type((j.get("job_types") or [None])[0]),
                description=_clean(j.get("description"))[:8000] or title,
                requirements=tags,
                keywords=tags,
                apply_url=j.get("url"),
                posted_at=_parse_epoch(j.get("created_at")),
            ))
            if len(out) >= limit:
                break
        log.info("arbeitnow_fetched", count=len(out), query=query)
        return out


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)


def _parse_epoch(value) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)
