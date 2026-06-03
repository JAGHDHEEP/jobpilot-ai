# JobPilot AI — System Architecture

## 1. High-level view

```
                          ┌─────────────────────────────────────────┐
                          │              Nginx (reverse proxy)        │
                          └───────────────┬───────────────┬──────────┘
                                          │               │
                          ┌───────────────▼──┐      ┌──────▼─────────────┐
                          │  Next.js 15 (SSR) │      │  FastAPI (ASGI)     │
                          │  React 19 / Zustand│◄────►│  /api/v1/*          │
                          └────────────────────┘ REST └──────┬─────────────┘
                                                              │
        ┌──────────────────┬───────────────┬─────────────────┼────────────────┐
        │                  │               │                 │                │
  ┌─────▼─────┐     ┌───────▼──────┐  ┌─────▼──────┐   ┌───────▼─────┐  ┌───────▼──────┐
  │PostgreSQL │     │   ChromaDB    │  │   Redis     │   │ Celery work │  │  AI providers │
  │(SQLAlchemy)│     │ (embeddings)  │  │(broker/cache)│  │ + beat      │  │ OpenAI/Claude │
  └───────────┘     └──────────────┘  └─────────────┘   └─────────────┘  └──────────────┘
```

## 2. Backend layering (clean / hexagonal)

```
api (routers, deps)  ->  services (use-cases)  ->  models/repos (persistence)
                           │
                           └──> ai (providers, RAG, matching, prompts)
                           └──> connectors (job sources, modular adapters)
                           └──> workers (Celery async tasks)
```

- **api** — thin HTTP layer: validation, auth, serialization. No business logic.
- **services** — orchestrate use-cases; transaction boundaries; call AI + repos.
- **models** — SQLAlchemy 2.0 ORM (async). One module per aggregate.
- **schemas** — Pydantic v2 DTOs; never expose ORM directly.
- **ai** — provider-agnostic `LLMClient` + `EmbeddingClient`; RAG pipeline over ChromaDB;
  prompt templates; evaluation harness; response caching keyed by content hash.
- **connectors** — each job source implements the `JobConnector` protocol; registered in a
  registry; swappable (API / RSS / scraper / browser-automation).

## 3. AI matching engine

Score is a weighted blend producing an explainable report:

| Component         | Weight | Method |
|-------------------|--------|--------|
| Skill match       | 30%    | Set overlap of normalized skills + semantic similarity for fuzzy matches |
| Project relevance | 25%    | Cosine similarity between project embeddings and JD embedding |
| Experience match  | 20%    | Years + role-title semantic match + seniority heuristic |
| Education match   | 10%    | Degree-level rule table vs. JD requirements |
| Keyword match     | 15%    | ATS keyword coverage (TF-weighted) |

Each component returns `(score, evidence, missing[])`. The LLM produces a natural-language
rationale **constrained to the computed numbers** (the numbers are deterministic; the LLM
only explains, it does not invent the score). Results persisted to `job_matches`.

## 4. RAG pipeline

1. On resume upload → parse → chunk → embed (`EmbeddingClient`) → upsert to ChromaDB
   collection `resumes:{user_id}` with metadata.
2. On job ingest → embed JD → store in `jobs` collection.
3. Matching/optimization → retrieve top-k profile chunks relevant to a JD → inject into
   prompt as grounded context (prevents hallucinated experience).

## 5. Async / scheduled work (Celery beat)

- `aggregate_jobs` (hourly) — run enabled connectors, dedupe, persist, embed.
- `score_new_jobs` (every 15 min) — score unscored jobs for active users.
- `build_daily_recommendations` (daily 06:00) — top-50 per user, ranked.
- `refresh_market_insights` (daily) — trending skills aggregation.

## 6. Security

JWT access (15m) + rotating refresh (7d, stored hashed + revocable). OAuth2 code flow.
Argon2 password hashing. RBAC (`user`, `admin`). Per-IP + per-user rate limiting (Redis
token bucket). Pydantic validation everywhere. Secure uploads (MIME sniff, size cap,
extension allowlist, AV-hook point). Audit log table for sensitive actions.

## 7. Scaling notes

Stateless API (horizontal scale behind Nginx/LB). Celery workers scale independently.
Postgres read replicas + PgBouncer for connection pooling. ChromaDB → swappable for
pgvector/Pinecone via the `VectorStore` interface. AI calls cached + batched; cost metered
per user in `ai_usage`.
