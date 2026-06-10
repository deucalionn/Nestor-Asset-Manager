# NAM development commands

sync:
    uv sync --all-packages

# --- Docker stack: db + migrate + api + agentic (+ front with `just app`) ---

up:
    docker compose up -d db --wait

down:
    docker compose --profile app down --remove-orphans

down-v:
    docker compose --profile app down -v --remove-orphans

logs:
    docker compose --profile app logs -f

migrate:
    uv run --directory packages/db alembic upgrade head

migrate-docker:
    docker compose run --rm migrate

back:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p data/agent_workspace/shared data/agent_workspace/user
    echo "Stack → API http://localhost:8000 | Agent http://localhost:8001"
    echo "Ollama must run on the host (ollama serve + ollama pull gemma4)"
    docker compose up --build --remove-orphans

app:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p data/agent_workspace/shared data/agent_workspace/user
    echo "Stack → API http://localhost:8000 | Agent http://localhost:8001 | Front http://localhost:3000"
    echo "Ollama must run on the host (ollama serve + ollama pull gemma4)"
    docker compose --profile app up --build --remove-orphans

# --- Local single service (debug without Docker) ---

front:
    cd front && pnpm dev

front-local:
    cd front && pnpm dev

api:
    uv run --directory api uvicorn nam_api.main:app --reload --host 0.0.0.0 --port 8000

agentic:
    uv run --directory agentic uvicorn nam_agentic.main:app --reload --host 0.0.0.0 --port 8001

# --- Tests & lint ---

test:
    docker compose -f docker/tests/docker-compose.test.yml up --build --abort-on-container-exit --remove-orphans

test-down:
    docker compose -f docker/tests/docker-compose.test.yml down -v --remove-orphans

lint:
    uv run ruff check .
