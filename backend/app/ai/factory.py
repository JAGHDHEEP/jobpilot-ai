"""Build the configured AI clients with caching + usage metering wrappers."""
from __future__ import annotations

import json
from functools import lru_cache

from app.ai.base import EmbeddingClient, LLMClient, LLMResponse, estimate_cost
from app.ai.cache import cache, cache_key
from app.ai.providers import (
    AnthropicLLM,
    MockEmbeddings,
    MockLLM,
    OpenAIEmbeddings,
    OpenAILLM,
)
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger()


class CachedLLM:
    """Decorator that adds content-hash caching around any LLMClient."""

    def __init__(self, inner: LLMClient) -> None:
        self.inner = inner
        self.provider = inner.provider
        self.model = inner.model

    async def complete(self, *, system, user, temperature=0.2, max_tokens=1500,
                       json_mode=False) -> LLMResponse:
        key = cache_key("llm", self.provider, self.model, system, user, temperature,
                        max_tokens, json_mode)
        cached = await cache.get(key)
        if cached is not None:
            return LLMResponse(text=cached["text"], model=self.model, provider=self.provider,
                               prompt_tokens=cached.get("pt", 0),
                               completion_tokens=cached.get("ct", 0), cache_hit=True)
        resp = await self.inner.complete(system=system, user=user, temperature=temperature,
                                         max_tokens=max_tokens, json_mode=json_mode)
        await cache.set(key, {"text": resp.text, "pt": resp.prompt_tokens,
                              "ct": resp.completion_tokens})
        return resp


def _build_llm() -> LLMClient:
    if settings.AI_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return CachedLLM(OpenAILLM())  # type: ignore[arg-type]
    if settings.AI_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
        return CachedLLM(AnthropicLLM())  # type: ignore[arg-type]
    log.info("ai_provider_mock", reason="no key or provider=mock")
    return CachedLLM(MockLLM())  # type: ignore[arg-type]


def _build_embeddings() -> EmbeddingClient:
    if settings.AI_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return OpenAIEmbeddings()
    return MockEmbeddings()


@lru_cache
def get_llm() -> LLMClient:
    return _build_llm()


@lru_cache
def get_embeddings() -> EmbeddingClient:
    return _build_embeddings()


def parse_json_response(resp: LLMResponse) -> dict:
    """Tolerant JSON extraction from an LLM response."""
    text = resp.text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    return {}


def usage_cost(resp: LLMResponse) -> float:
    return estimate_cost(resp.model, resp.prompt_tokens, resp.completion_tokens)
