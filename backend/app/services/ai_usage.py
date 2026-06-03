"""Persist AI usage records for metering and admin reporting."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import LLMResponse, estimate_cost
from app.models.system import AIUsage


async def record_usage(db: AsyncSession, *, user_id: str | None, operation: str,
                       resp: LLMResponse) -> None:
    usage = AIUsage(
        user_id=user_id,
        provider=resp.provider,
        model=resp.model,
        operation=operation,
        prompt_tokens=resp.prompt_tokens,
        completion_tokens=resp.completion_tokens,
        cost_usd=estimate_cost(resp.model, resp.prompt_tokens, resp.completion_tokens),
        cache_hit=resp.cache_hit,
        created_at=datetime.now(timezone.utc),
    )
    db.add(usage)
    await db.flush()
