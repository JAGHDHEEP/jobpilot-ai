# Implementation status & roadmap

Legend: ✅ implemented · 🟡 scaffolded (interface + stub, ready to extend) · ⬜ planned

## Backend
- ✅ App factory, config, logging, exception handlers, CORS, rate limiting
- ✅ Async SQLAlchemy engine/session, declarative base, Alembic
- ✅ All ORM models for the full schema
- ✅ Pydantic v2 schemas (auth, profile, jobs, matches, applications)
- ✅ Auth: register/login, JWT access+refresh, Argon2, RBAC deps
- 🟡 OAuth2 (Google/GitHub) — flow + callback wiring point
- ✅ Profile service + CRUD routers (profile, education, experience, projects, skills…)
- ✅ Resume parsing engine (PDF/DOCX → structured master profile)
- ✅ AI provider abstraction (OpenAI + Claude) + caching + usage metering
- ✅ Embedding client + ChromaDB vector store + RAG retrieval
- ✅ Job matching engine (deterministic weighted score + LLM rationale)
- ✅ Resume optimization service (ATS, grounded, truthful)
- ✅ Cover letter + interview prep + resume review services
- 🟡 Job connectors: base protocol + registry + Indeed/RSS/manual adapters
   (LinkedIn/Naukri/Foundit/Wellfound/Glassdoor adapters stubbed to the same interface)
- ✅ Application tracker + analytics endpoints
- ✅ Recommendation engine + ranking
- 🟡 Celery tasks + beat schedule (aggregate/score/recommend/insights)
- ✅ Admin endpoints (users, jobs, ai-usage, audit)
- ✅ Pytest suite (unit + API integration) + fixtures

## Frontend
- ✅ Next.js 15 app scaffold, Tailwind, theme/dark-mode, Zustand store, API client
- ✅ Landing, login, register, dashboard, job matches, profile pages
- 🟡 Resume optimizer, application tracker, interview prep, settings, admin (scaffolded)

## Infra
- ✅ Backend + frontend Dockerfiles, docker-compose (api/worker/beat/db/redis/chroma/nginx)
- ✅ Nginx reverse proxy config
- ✅ GitHub Actions CI (lint, type-check, test) + build
- ✅ .env.example, deployment guide
```
