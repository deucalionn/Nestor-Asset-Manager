# NAM development commands

sync:
    uv sync --all-packages

up:
    docker compose up -d

down:
    docker compose down

migrate:
    uv run --directory packages/db alembic upgrade head

api:
    uv run uvicorn nam_api.main:app --reload --host 0.0.0.0 --port 8000

worker:
    uv run python -m nam_agentic.scheduler.worker

lint:
    uv run ruff check .
