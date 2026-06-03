.PHONY: up down logs test lint fmt migrate seed backend frontend

up:        ## Build & start the full stack
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f api worker

test:      ## Run backend tests
	cd backend && pytest

lint:
	cd backend && ruff check app tests && mypy app || true

fmt:
	cd backend && ruff check --fix app tests

migrate:   ## Apply DB migrations
	docker compose exec api alembic upgrade head

seed:      ## Seed admin + demo jobs
	docker compose exec api python -m app.db.init_db

backend:   ## Run API locally (needs venv + .env)
	cd backend && uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev
