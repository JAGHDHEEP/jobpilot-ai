"""Generic RSS/Atom job-feed connector.

Many boards (and company career pages) expose RSS. This adapter is reused by concrete
sources by subclassing and setting `feed_url` + `source`.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import httpx

from app.connectors.base import JobConnector
from app.core.logging import get_logger
from app.models.enums import JobSource
from app.schemas.job import JobCreate

log = get_logger()
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub(" ", text or "").strip()


class RSSConnector(JobConnector):
    mechanism = "rss"
    source = JobSource.company
    feed_url: str = ""

    def __init__(self, feed_url: str | None = None, source: JobSource | None = None):
        if feed_url:
            self.feed_url = feed_url
        if source:
            self.source = source

    async def fetch(self, *, query="", location="", limit=50) -> list[JobCreate]:
        if not self.feed_url:
            return []
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(self.feed_url)
                resp.raise_for_status()
            return self._parse(resp.text, limit)
        except Exception as exc:  # pragma: no cover - network best-effort
            log.warning("rss_fetch_failed", url=self.feed_url, error=str(exc))
            return []

    def _parse(self, xml: str, limit: int) -> list[JobCreate]:
        jobs: list[JobCreate] = []
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            return []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            desc = _strip_html(item.findtext("description") or "")
            link = (item.findtext("link") or "").strip()
            if not title:
                continue
            company = "Unknown"
            if " at " in title:
                title, company = (p.strip() for p in title.split(" at ", 1))
            jobs.append(JobCreate(
                source=self.source, title=title, company=company,
                description=desc or title, apply_url=link or None,
                posted_at=datetime.now(timezone.utc),
            ))
            if len(jobs) >= limit:
                break
        return jobs
