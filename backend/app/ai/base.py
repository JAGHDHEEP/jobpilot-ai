"""Provider-agnostic AI interfaces and data structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class LLMResponse:
    text: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_hit: bool = False
    raw: dict = field(default_factory=dict)


@runtime_checkable
class LLMClient(Protocol):
    """Chat-completion style text generation."""

    provider: str
    model: str

    async def complete(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        json_mode: bool = False,
    ) -> LLMResponse: ...


@runtime_checkable
class EmbeddingClient(Protocol):
    provider: str
    model: str
    dim: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


# Rough public per-1K-token pricing (USD) for cost metering. Override via config if needed.
PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.01),
    "text-embedding-3-small": (0.00002, 0.0),
    "claude-sonnet-4-6": (0.003, 0.015),
    "mock": (0.0, 0.0),
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pin, pout = PRICING.get(model, (0.0, 0.0))
    return round(pin * prompt_tokens / 1000 + pout * completion_tokens / 1000, 6)
