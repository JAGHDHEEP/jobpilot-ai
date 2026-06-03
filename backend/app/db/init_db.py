"""Create tables directly + seed an admin and demo jobs (dev/bootstrap helper).

For production use Alembic migrations. This is a convenience entrypoint for local dev
and the docker `api` container's first boot when ALEMBIC isn't run.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.connectors import enabled_connectors
from app.core.logging import get_logger
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.enums import UserRole
from app.models.profile import Profile
from app.models.user import User
from app.services import job_service

log = get_logger()


async def create_all() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed() -> None:
    async with SessionLocal() as db:
        admin = (await db.execute(
            select(User).where(User.email == "admin@jobpilot.ai"))).scalar_one_or_none()
        if not admin:
            admin = User(email="admin@jobpilot.ai", full_name="Admin",
                         hashed_password=hash_password("admin12345"), role=UserRole.admin,
                         is_verified=True)
            db.add(admin)
            await db.flush()
            db.add(Profile(user_id=admin.id))
            log.info("seed_admin_created", email="admin@jobpilot.ai")

        jobs_count = 0
        for connector in enabled_connectors():
            for item in await connector.fetch(limit=20):
                await job_service.upsert_job(db, item)
                jobs_count += 1
        await db.commit()
        log.info("seed_done", jobs=jobs_count, ts=datetime.now(timezone.utc).isoformat())


async def main() -> None:
    await create_all()
    await seed()


if __name__ == "__main__":
    asyncio.run(main())
