"""FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import RateLimitMiddleware

configure_logging()
log = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", env=settings.ENV, ai_provider=settings.AI_PROVIDER)
    import app.connectors  # noqa: F401  ensure connectors are registered
    if settings.AUTO_SEED:
        try:
            from app.db.init_db import create_all, seed
            await create_all()      # idempotent; safe alongside Alembic
            await seed()            # creates admin + demo jobs only if missing
            log.info("auto_seed_done")
        except Exception as exc:  # never let seeding crash the app
            log.warning("auto_seed_failed", error=str(exc))
    yield
    log.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        description="AI-powered job search & resume optimization platform.",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    if settings.CORS_ALLOW_ALL or "*" in settings.BACKEND_CORS_ORIGINS:
        # Wildcard origin requires credentials disabled (we use Bearer tokens, not cookies).
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=".*",
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.BACKEND_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(RateLimitMiddleware)
    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["system"])
    async def health() -> dict:
        return {"status": "ok", "env": settings.ENV}

    return app


app = create_app()
