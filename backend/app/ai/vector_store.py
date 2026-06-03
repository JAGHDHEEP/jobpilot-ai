"""Vector store abstraction over ChromaDB with an in-memory fallback."""
from __future__ import annotations

from dataclasses import dataclass

from app.ai.factory import get_embeddings
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger()


@dataclass
class SearchHit:
    id: str
    text: str
    score: float
    metadata: dict


class VectorStore:
    """Thin wrapper. Uses ChromaDB if reachable, else a cosine in-memory index."""

    def __init__(self) -> None:
        self._client = None
        self._mem: dict[str, dict[str, dict]] = {}   # collection -> id -> {text,emb,meta}
        self._embed = get_embeddings()

    def _chroma(self):
        if self._client is not None:
            return self._client
        try:
            import chromadb
            self._client = chromadb.HttpClient(host=settings.CHROMA_HOST,
                                                port=settings.CHROMA_PORT)
            self._client.heartbeat()
        except Exception:  # pragma: no cover - fallback path
            log.info("chroma_unavailable_using_memory")
            self._client = None
        return self._client

    async def upsert(self, collection: str, ids: list[str], texts: list[str],
                     metadatas: list[dict]) -> None:
        embeddings = await self._embed.embed(texts)
        client = self._chroma()
        if client is not None:
            coll = client.get_or_create_collection(collection)
            coll.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
            return
        store = self._mem.setdefault(collection, {})
        for i, t, e, m in zip(ids, texts, embeddings, metadatas, strict=True):
            store[i] = {"text": t, "emb": e, "meta": m}

    async def query(self, collection: str, text: str, k: int = 5,
                    where: dict | None = None) -> list[SearchHit]:
        q_emb = (await self._embed.embed([text]))[0]
        client = self._chroma()
        if client is not None:
            try:
                coll = client.get_collection(collection)
            except Exception:
                return []
            res = coll.query(query_embeddings=[q_emb], n_results=k, where=where)
            hits: list[SearchHit] = []
            for i in range(len(res["ids"][0])):
                hits.append(SearchHit(
                    id=res["ids"][0][i], text=res["documents"][0][i],
                    score=1.0 - float(res["distances"][0][i]),
                    metadata=res["metadatas"][0][i] or {}))
            return hits
        return self._mem_query(collection, q_emb, k, where)

    def _mem_query(self, collection, q_emb, k, where) -> list[SearchHit]:
        store = self._mem.get(collection, {})
        scored = []
        for id_, rec in store.items():
            if where and not all(rec["meta"].get(kk) == vv for kk, vv in where.items()):
                continue
            scored.append(SearchHit(id_, rec["text"], _cosine(q_emb, rec["emb"]), rec["meta"]))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:k]

    async def delete(self, collection: str, where: dict) -> None:
        client = self._chroma()
        if client is not None:
            try:
                client.get_collection(collection).delete(where=where)
            except Exception:
                pass
            return
        store = self._mem.get(collection, {})
        for id_ in [i for i, r in store.items()
                    if all(r["meta"].get(k) == v for k, v in where.items())]:
            store.pop(id_, None)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    return dot  # embeddings are pre-normalized


_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
