"""Idempotent, self-healing schema bootstrap.

The live database was originally created with ``create_all`` (not Alembic), so running
Alembic from base against it is fragile. Instead, on every startup we:
  1. ``create_all`` — create any missing tables,
  2. add any missing columns to ``profiles`` (ALTER TABLE),
  3. add any missing values to the ``job_source`` enum (PostgreSQL only).

All steps are idempotent and safe to run repeatedly. Alembic migrations remain in the
repo as the source-of-truth history, but are not required at boot.
"""
from __future__ import annotations

from sqlalchemy import inspect, text

import app.models  # noqa: F401  registers all ORM tables on Base.metadata
from app.core.logging import get_logger
from app.db.base import Base
from app.db.session import engine

log = get_logger()

# Columns added after the initial schema. (name -> column type SQL, json flag)
_PROFILE_COLUMNS: list[tuple[str, str, bool]] = [
    ("current_role", "VARCHAR(200)", False),
    ("years_experience", "NUMERIC(4,1)", False),
    ("current_ctc", "VARCHAR(60)", False),
    ("expected_ctc", "VARCHAR(60)", False),
    ("notice_period", "VARCHAR(60)", False),
    ("work_mode", "VARCHAR(20)", False),
    ("preferred_locations", "JSON", True),
    ("preferred_titles", "JSON", True),
    ("salary_min", "NUMERIC(12,2)", False),
    ("salary_max", "NUMERIC(12,2)", False),
]

_NEW_JOB_SOURCES = ("remotive", "arbeitnow")


async def ensure_schema() -> None:
    # 1) create missing tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2) add missing profile columns
    async with engine.begin() as conn:
        await conn.run_sync(_add_missing_profile_columns)

    # 3) add missing enum values (PostgreSQL needs autocommit for ALTER TYPE ADD VALUE)
    if engine.dialect.name == "postgresql":
        async with engine.connect() as conn:
            ac = await conn.execution_options(isolation_level="AUTOCOMMIT")
            for value in _NEW_JOB_SOURCES:
                try:
                    await ac.exec_driver_sql(
                        f"ALTER TYPE job_source ADD VALUE IF NOT EXISTS '{value}'")
                except Exception as exc:  # pragma: no cover
                    log.warning("enum_add_value_failed", value=value, error=str(exc))
    log.info("ensure_schema_done")


def _add_missing_profile_columns(sync_conn) -> None:
    insp = inspect(sync_conn)
    if "profiles" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("profiles")}
    is_pg = sync_conn.dialect.name == "postgresql"
    for name, sqltype, is_json in _PROFILE_COLUMNS:
        if name in existing:
            continue
        default = ""
        if is_json:
            default = " DEFAULT '[]'::json" if is_pg else " DEFAULT '[]'"
        sync_conn.execute(text(f'ALTER TABLE profiles ADD COLUMN {name} {sqltype}{default}'))
        log.info("added_profile_column", column=name)
