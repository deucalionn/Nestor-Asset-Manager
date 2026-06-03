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

test:
    docker compose -f docker/tests/docker-compose.test.yml up --build --abort-on-container-exit --remove-orphans

test-down:
    docker compose -f docker/tests/docker-compose.test.yml down -v --remove-orphans

lint:
    uv run ruff check .
