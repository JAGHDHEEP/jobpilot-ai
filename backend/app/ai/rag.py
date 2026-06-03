"""RAG helpers: index a profile and retrieve grounded context for a job."""
from __future__ import annotations

from app.ai.vector_store import get_vector_store
from app.schemas.document import ParsedProfile

PROFILE_COLLECTION = "profiles"
JOB_COLLECTION = "jobs"


def _profile_chunks(profile: ParsedProfile) -> list[str]:
    chunks: list[str] = []
    if profile.summary:
        chunks.append(f"Summary: {profile.summary}")
    if profile.skills:
        chunks.append("Skills: " + ", ".join(profile.skills))
    for e in profile.experiences:
        chunks.append(
            f"Experience: {e.get('role', '')} at {e.get('company', '')}. "
            f"{e.get('description', '')} "
            + " ".join(e.get("highlights", []) or [])
        )
    for p in profile.projects:
        chunks.append(
            f"Project: {p.get('title', '')}. {p.get('description', '')} "
            f"Tech: {', '.join(p.get('technologies', []) or [])}"
        )
    for ed in profile.educations:
        chunks.append(f"Education: {ed.get('degree', '')} from {ed.get('institution', '')}")
    return [c for c in chunks if c.strip()]


async def index_profile(user_id: str, profile: ParsedProfile) -> int:
    store = get_vector_store()
    await store.delete(PROFILE_COLLECTION, {"user_id": user_id})
    chunks = _profile_chunks(profile)
    if not chunks:
        return 0
    ids = [f"{user_id}:{i}" for i in range(len(chunks))]
    metas = [{"user_id": user_id, "chunk": i} for i in range(len(chunks))]
    await store.upsert(PROFILE_COLLECTION, ids, chunks, metas)
    return len(chunks)


async def retrieve_profile_context(user_id: str, job_description: str, k: int = 6) -> str:
    store = get_vector_store()
    hits = await store.query(PROFILE_COLLECTION, job_description, k=k, where={"user_id": user_id})
    return "\n".join(f"- {h.text}" for h in hits)


async def index_job(job_id: str, title: str, description: str) -> None:
    store = get_vector_store()
    await store.upsert(JOB_COLLECTION, [job_id], [f"{title}\n{description}"],
                       [{"job_id": job_id}])
