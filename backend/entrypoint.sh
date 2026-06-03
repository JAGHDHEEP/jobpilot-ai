#!/usr/bin/env bash
set -euo pipefail

# Wait for Postgres, run migrations, then start the API.
echo "Running database migrations..."
alembic upgrade head || python -m app.db.init_db

exec "$@"
