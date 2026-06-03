"""Job connector protocol + registry.

Every job source implements `JobConnector`. Connectors are registered by name so the
aggregation worker can iterate enabled sources uniformly, regardless of whether the
underlying mechanism is a REST API, an RSS feed, a scraper, or browser automation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.enums import JobSource
from app.schemas.job import JobCreate


class JobConnector(ABC):
    source: JobSource
    #: api | rss | scrape | browser
    mechanism: str = "api"
    enabled: bool = True

    @abstractmethod
    async def fetch(self, *, query: str = "", location: str = "",
                    limit: int = 50) -> list[JobCreate]:
        """Return normalized JobCreate items. Must never raise on empty results."""
        raise NotImplementedError


_REGISTRY: dict[str, JobConnector] = {}


def register(connector: JobConnector) -> JobConnector:
    _REGISTRY[connector.source.value] = connector
    return connector


def get_connector(name: str) -> JobConnector | None:
    return _REGISTRY.get(name)


def enabled_connectors() -> list[JobConnector]:
    return [c for c in _REGISTRY.values() if c.enabled]


def all_connectors() -> dict[str, JobConnector]:
    return dict(_REGISTRY)
