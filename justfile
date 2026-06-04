# NAM development commands

sync:
    uv sync --all-packages

up:
    docker compose up -d

down:
    docker compose down

migrate:
    uv run --directory packages/db alembic upgrade head

# --- Stacks: `just back` | `just front` | `just app` ---

back:
    #!/usr/bin/env bash
    set -euo pipefail
    just up
    just migrate
    trap 'kill $(jobs -p) 2>/dev/null || true' EXIT INT TERM
    echo "API → http://localhost:8000  |  Agent → http://localhost:8001"
    uv run uvicorn nam_api.main:app --reload --host 0.0.0.0 --port 8000 &
    uv run uvicorn nam_agentic.main:app --reload --host 0.0.0.0 --port 8001 &
    wait

front:
    cd front && pnpm dev

app:
    #!/usr/bin/env bash
    set -euo pipefail
    just up
    just migrate
    trap 'kill $(jobs -p) 2>/dev/null || true' EXIT INT TERM
    echo "API → http://localhost:8000  |  Agent → http://localhost:8001  |  Front → http://localhost:3000"
    uv run uvicorn nam_api.main:app --reload --host 0.0.0.0 --port 8000 &
    uv run uvicorn nam_agentic.main:app --reload --host 0.0.0.0 --port 8001 &
    (cd front && pnpm dev) &
    wait

# --- Single service (debug) ---

api:
    uv run uvicorn nam_api.main:app --reload --host 0.0.0.0 --port 8000

agentic:
    uv run uvicorn nam_agentic.main:app --reload --host 0.0.0.0 --port 8001

# --- Tests & lint ---

test:
    docker compose -f docker/tests/docker-compose.test.yml up --build --abort-on-container-exit --remove-orphans

test-down:
    docker compose -f docker/tests/docker-compose.test.yml down -v --remove-orphans

lint:
    uv run ruff check .
