"""Redis-backed token-bucket rate limiting middleware.

Falls back to an in-process bucket when Redis is unavailable (dev/tests).
"""
from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

try:  # optional dependency at runtime
    import redis.asyncio as aioredis
except Exception:  # pragma: no cover
    aioredis = None  # type: ignore


_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local count = redis.call('INCR', key)
if count == 1 then redis.call('EXPIRE', key, window) end
return count
"""


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int | None = None, window: int = 60):
        super().__init__(app)
        self.limit = limit or settings.RATE_LIMIT_PER_MINUTE
        self.window = window
        self._redis = None
        self._local: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))

    async def _get_redis(self):
        if aioredis is None:
            return None
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                await self._redis.ping()
            except Exception:  # pragma: no cover
                self._redis = None
        return self._redis

    def _identity(self, request: Request) -> str:
        auth = request.headers.get("authorization", "")
        if auth:
            return f"u:{hash(auth)}"
        client = request.client.host if request.client else "anon"
        return f"ip:{client}"

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in ("/health", "/metrics") or request.method == "OPTIONS":
            return await call_next(request)

        key = f"rl:{self._identity(request)}:{int(time.time() // self.window)}"
        count = await self._increment(key)
        if count > self.limit:
            return JSONResponse(
                content={"error": {"code": "rate_limited",
                                   "message": "Too many requests"}},
                status_code=429,
                headers={"Retry-After": str(self.window)},
            )
        resp = await call_next(request)
        resp.headers["X-RateLimit-Limit"] = str(self.limit)
        resp.headers["X-RateLimit-Remaining"] = str(max(0, self.limit - count))
        return resp

    async def _increment(self, key: str) -> int:
        r = await self._get_redis()
        if r is not None:
            try:
                return int(await r.eval(_LUA, 1, key, int(time.time()), self.window, self.limit))
            except Exception:  # pragma: no cover
                pass
        # in-process fallback
        count, exp = self._local[key]
        now = time.time()
        if now > exp:
            count, exp = 0, now + self.window
        count += 1
        self._local[key] = (count, exp)
        return count
