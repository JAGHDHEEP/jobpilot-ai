# Deployment Guide

## Local (Docker Compose)

```bash
cp .env.example .env
# set SECRET_KEY and (optionally) OPENAI_API_KEY / ANTHROPIC_API_KEY + AI_PROVIDER
docker compose up --build
```

Services:

| Service  | URL / port | Notes |
|----------|------------|-------|
| nginx    | http://localhost (80) | single entry point |
| frontend | http://localhost:3000 | Next.js |
| api      | http://localhost:8000/docs | FastAPI + Swagger |
| postgres | localhost:5432 | data volume `pgdata` |
| redis    | localhost:6379 | broker + cache |
| chroma   | localhost:8001 | vector store |

On first boot the API container runs `alembic upgrade head` (falling back to
`python -m app.db.init_db`, which also seeds an admin `admin@jobpilot.ai / admin12345`
and demo jobs).

## Database migrations

```bash
docker compose exec api alembic revision --autogenerate -m "describe change"
docker compose exec api alembic upgrade head
```

## Production notes

- **Secrets**: inject `SECRET_KEY`, DB creds, and AI keys via your platform's secret
  manager (AWS Secrets Manager / Azure Key Vault / GCP Secret Manager) — never bake into
  images.
- **TLS**: terminate at the load balancer (ALB / App Gateway / GCLB) or add a `certbot`
  sidecar to Nginx. Set `OAUTH_REDIRECT_BASE` and CORS origins to the HTTPS domain.
- **Scaling**: `api`, `worker` are stateless — scale horizontally. Put PgBouncer in front
  of Postgres. Use a managed Redis (ElastiCache / Azure Cache / Memorystore) and managed
  Postgres (RDS / Azure DB / Cloud SQL).
- **Vector store**: ChromaDB persists to a volume; for HA swap the `VectorStore`
  implementation for pgvector or a managed vector DB (interface in
  `app/ai/vector_store.py`).
- **Object storage**: replace local `UPLOAD_DIR` with S3/GCS/Blob by implementing a
  storage adapter; `documents.storage_key` already models an object key.

### Cloud targets

- **AWS**: ECS Fargate (api/worker/beat) + RDS Postgres + ElastiCache Redis + ALB + S3.
- **Azure**: Container Apps + Azure DB for Postgres + Azure Cache for Redis + Blob.
- **GCP**: Cloud Run (api) + Cloud Run Jobs/GKE (worker) + Cloud SQL + Memorystore + GCS.

## Monitoring, logging, backups

- **Logs**: structured JSON (structlog) in non-dev — ship to CloudWatch / Log Analytics /
  Cloud Logging.
- **Metrics**: `/health` for liveness; add Prometheus middleware + `/metrics` for RED
  metrics; AI cost/usage is queryable via `GET /api/v1/admin/ai-usage`.
- **Backups**: enable automated Postgres snapshots (PITR). Snapshot the Chroma volume
  nightly. Test restores quarterly.
- **Rollback**: images are tagged per commit; redeploy the previous tag and run
  `alembic downgrade -1` only if a migration must be reverted.
