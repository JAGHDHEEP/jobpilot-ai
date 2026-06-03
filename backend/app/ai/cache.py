"""Content-hash response cache (Redis with in-process fallback)."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from app.core.config import settings

try:
    import redis.asyncio as aioredis
except Exception:  # pragma: no cover
    aioredis = None  # type: ignore

_TTL = 60 * 60 * 24 * 7  # 7 days


def cache_key(*parts: Any) -> str:
    blob = json.dumps(parts, sort_keys=True, default=str)
    return "ai:" + hashlib.sha256(blob.encode()).hexdigest()


class ResponseCache:
    def __init__(self) -> None:
        self._redis = None
        self._local: dict[str, str] = {}

    async def _r(self):
        if aioredis is None:
            return None
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                await self._redis.ping()
            except Exception:  # pragma: no cover
                self._redis = None
        return self._redis

    async def get(self, key: str) -> dict | None:
        r = await self._r()
        raw: str | None
        if r is not None:
            try:
                raw = await r.get(key)
            except Exception:  # pragma: no cover
                raw = self._local.get(key)
        else:
            raw = self._local.get(key)
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: dict, ttl: int = _TTL) -> None:
        raw = json.dumps(value)
        r = await self._r()
        if r is not None:
            try:
                await r.set(key, raw, ex=ttl)
                return
            except Exception:  # pragma: no cover
                pass
        self._local[key] = raw


cache = ResponseCache()
