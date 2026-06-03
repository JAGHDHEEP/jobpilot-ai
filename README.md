# JobPilot AI

An AI-powered job search & resume optimization platform. JobPilot stores a user's
complete professional profile, parses resumes into a structured master profile,
aggregates jobs from multiple sources, scores each job against the profile with an
explainable AI matching engine, generates ATS-optimized tailored resumes and cover
letters, recommends the best jobs daily, tracks applications, and helps with interview
prep.

> **Status:** This repository is a production-shaped MVP. The architecture, database
> schema, authentication, profile system, resume-parsing engine, AI service layer, and
> the job-matching engine are implemented end-to-end. Connectors, the full frontend, and
> the remaining feature surfaces are scaffolded with clear extension points (see
> [docs/ROADMAP.md](docs/ROADMAP.md)).

## Tech stack

| Layer        | Technology |
|--------------|-----------|
| Frontend     | Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui, Framer Motion, Zustand |
| Backend      | FastAPI, Python 3.12, Pydantic v2 |
| Database     | PostgreSQL 16 + SQLAlchemy 2.0 (async) + Alembic |
| Auth         | JWT (access/refresh) + OAuth2 (Google/GitHub) + RBAC |
| AI           | OpenAI + Anthropic Claude (pluggable provider abstraction) |
| Vector DB    | ChromaDB |
| Async jobs   | Celery + Redis (broker + result + cache) |
| Deployment   | Docker, Docker Compose, Nginx |

## Repository layout

```
jobpilot-ai/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/             # Routers (v1), dependencies
│   │   ├── core/           # Config, security, logging, rate limiting
│   │   ├── db/             # Engine, session, base
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response models
│   │   ├── services/       # Business logic
│   │   ├── ai/             # AI provider abstraction, RAG, prompts, matching
│   │   ├── connectors/     # Modular job-source connectors
│   │   ├── workers/        # Celery tasks & beat schedules
│   │   └── main.py         # App factory
│   ├── alembic/            # Migrations
│   ├── tests/              # Pytest suite
│   └── pyproject.toml
├── frontend/               # Next.js 15 app
├── infra/                  # Nginx, docker, deployment
├── docs/                   # Architecture, schema, ROADMAP
├── docker-compose.yml
└── .github/workflows/      # CI/CD
```

## Quick start (Docker)

```bash
cp .env.example .env          # fill in secrets / API keys
docker compose up --build
# API      -> http://localhost:8000/docs
# Frontend -> http://localhost:3000
# Postgres -> localhost:5432
```

## Local backend dev

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
