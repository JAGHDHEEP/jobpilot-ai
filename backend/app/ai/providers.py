"""Concrete LLM / embedding providers: OpenAI, Anthropic, and a deterministic mock."""
from __future__ import annotations

import hashlib
import json
import math
import re

from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.base import EmbeddingClient, LLMClient, LLMResponse
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger()
_RETRY = dict(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)


# --------------------------------------------------------------------------- OpenAI
class OpenAILLM(LLMClient):
    provider = "openai"

    def __init__(self) -> None:
        from openai import AsyncOpenAI
        self.model = settings.OPENAI_MODEL
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    @retry(**_RETRY)
    async def complete(self, *, system, user, temperature=0.2, max_tokens=1500,
                       json_mode=False) -> LLMResponse:
        kwargs: dict = {"response_format": {"type": "json_object"}} if json_mode else {}
        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        usage = resp.usage
        return LLMResponse(
            text=resp.choices[0].message.content or "",
            model=self.model, provider=self.provider,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )


class OpenAIEmbeddings(EmbeddingClient):
    provider = "openai"
    dim = 1536

    def __init__(self) -> None:
        from openai import AsyncOpenAI
        self.model = settings.OPENAI_EMBED_MODEL
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    @retry(**_RETRY)
    async def embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in resp.data]


# --------------------------------------------------------------------------- Anthropic
class AnthropicLLM(LLMClient):
    provider = "anthropic"

    def __init__(self) -> None:
        from anthropic import AsyncAnthropic
        self.model = settings.ANTHROPIC_MODEL
        self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    @retry(**_RETRY)
    async def complete(self, *, system, user, temperature=0.2, max_tokens=1500,
                       json_mode=False) -> LLMResponse:
        if json_mode:
            system += "\n\nRespond with ONLY a single valid JSON object, no prose."
        resp = await self._client.messages.create(
            model=self.model, system=system,
            messages=[{"role": "user", "content": user}],
            temperature=temperature, max_tokens=max_tokens,
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        return LLMResponse(
            text=text, model=self.model, provider=self.provider,
            prompt_tokens=resp.usage.input_tokens, completion_tokens=resp.usage.output_tokens,
        )


# --------------------------------------------------------------------------- Mock
class MockLLM(LLMClient):
    """Deterministic, offline provider for dev/tests. Produces plausible JSON."""

    provider = "mock"
    model = "mock"

    async def complete(self, *, system, user, temperature=0.2, max_tokens=1500,
                       json_mode=False) -> LLMResponse:
        if json_mode:
            text = json.dumps(self._mock_json(system, user))
        else:
            text = self._mock_prose(user)
        return LLMResponse(text=text, model=self.model, provider=self.provider,
                           prompt_tokens=len(user) // 4, completion_tokens=len(text) // 4)

    @staticmethod
    def _mock_json(system: str, user: str) -> dict:
        s = system.lower()
        if "rationale" in s or "match" in s:
            return {"rationale": "Strong overlap on core skills and relevant projects; "
                                 "gaps in a few infrastructure keywords."}
        if "interview" in s:
            return {"questions": [
                {"category": "behavioral", "question": "Tell me about a hard bug you fixed.",
                 "guidance": "Use STAR; quantify impact."},
                {"category": "technical", "question": "Explain how you'd design a rate limiter.",
                 "guidance": "Discuss token bucket, Redis, trade-offs."},
                {"category": "project", "question": "Walk through your most relevant project.",
                 "guidance": "Tie tech choices to the role."},
                {"category": "company", "question": "Why this company?",
                 "guidance": "Reference mission + recent work."}]}
        if "review" in s or "ats" in s:
            return {"ats_score": 78, "formatting_score": 80, "keyword_score": 72,
                    "impact_score": 75, "project_quality_score": 82, "skill_relevance_score": 79,
                    "sections": [{"name": "Summary", "score": 80, "feedback": "Tighten to 3 lines."}],
                    "suggestions": ["Add metrics to bullets.", "Surface cloud keywords."]}
        if "parse" in s or "extract" in s:
            return MockLLM._parse_resume(user)
        return {"result": "ok"}

    @staticmethod
    def _parse_resume(text: str) -> dict:
        skills = sorted({w for w in re.findall(r"[A-Za-z+#.]{2,}", text)
                         if w.lower() in _COMMON_SKILLS})
        return {"full_name": None, "skills": skills[:30], "experiences": [],
                "educations": [], "projects": [], "certifications": [],
                "keywords": skills[:30], "summary": None}

    @staticmethod
    def _mock_prose(user: str) -> str:
        return ("Dear Hiring Manager,\n\nI am excited to apply. My background aligns closely "
                "with your requirements, and I have delivered measurable results in similar "
                "roles.\n\nSincerely,\nCandidate")


class MockEmbeddings(EmbeddingClient):
    """Deterministic hashing embedding — stable across runs, no network."""

    provider = "mock"
    model = "mock"
    dim = 256

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in re.findall(r"\w+", text.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


_COMMON_SKILLS = {
    "python", "java", "javascript", "typescript", "react", "node", "fastapi", "django",
    "flask", "sql", "postgresql", "mysql", "mongodb", "redis", "docker", "kubernetes", "aws",
    "azure", "gcp", "terraform", "git", "ci", "cd", "graphql", "rest", "kafka", "spark",
    "pytorch", "tensorflow", "pandas", "numpy", "go", "rust", "c++", "html", "css", "tailwind",
    "nextjs", "celery", "rabbitmq", "linux", "bash", "ml", "nlp", "llm",
}
