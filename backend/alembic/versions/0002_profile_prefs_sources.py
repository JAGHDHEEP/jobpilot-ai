"""Add profile professional/preference fields + new job sources.

Revision ID: 0002_profile_prefs
Revises: 0001_initial
Create Date: 2026-06-07
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_profile_prefs"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON_DEFAULT = sa.text("'[]'")


def upgrade() -> None:
    bind = op.get_bind()
    existing = {c["name"] for c in sa.inspect(bind).get_columns("profiles")}

    # Idempotent: only add columns that don't already exist. (The 0001 baseline uses
    # create_all of current metadata, so a *fresh* DB already has these columns, while a
    # DB created before this revision does not — this handles both safely.)
    cols = [
        sa.Column("current_role", sa.String(200), nullable=True),
        sa.Column("years_experience", sa.Numeric(4, 1), nullable=True),
        sa.Column("current_ctc", sa.String(60), nullable=True),
        sa.Column("expected_ctc", sa.String(60), nullable=True),
        sa.Column("notice_period", sa.String(60), nullable=True),
        sa.Column("work_mode", sa.String(20), nullable=True),
        sa.Column("preferred_locations", sa.JSON(), nullable=False, server_default=_JSON_DEFAULT),
        sa.Column("preferred_titles", sa.JSON(), nullable=False, server_default=_JSON_DEFAULT),
        sa.Column("salary_min", sa.Numeric(12, 2), nullable=True),
        sa.Column("salary_max", sa.Numeric(12, 2), nullable=True),
    ]
    for col in cols:
        if col.name not in existing:
            op.add_column("profiles", col)

    # New enum values for job_source (PostgreSQL only; SQLite stores enums as VARCHAR).
    # ADD VALUE must run outside the migration transaction -> use autocommit_block.
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            for value in ("remotive", "arbeitnow"):
                op.execute(f"ALTER TYPE job_source ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    for col in ("salary_max", "salary_min", "preferred_titles", "preferred_locations",
                "work_mode", "notice_period", "expected_ctc", "current_ctc",
                "years_experience", "current_role"):
        op.drop_column("profiles", col)
    # Note: removing a value from a PostgreSQL enum is not supported; left in place.
