# Nestor Asset Manager (NAM)

Autonomous financial decision-support platform built as a uv monorepo with three Python packages:

- **nam-db** — shared SQLAlchemy models, enums, Alembic migrations
- **nam-agentic** — Deep Agents harness, tools, market scheduler worker
- **nam-api** — FastAPI REST + WebSocket entry point

## Prerequisites

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) — **required**
- [just](https://github.com/casey/just) — optional shortcuts (`brew install just` on macOS)
- Docker + Docker Compose

## Setup

### Python environment (uv)

`uv` creates and manages a virtual environment at `.venv/` in the repo root. You do **not** need `python -m venv` manually.

```bash
# Creates .venv (if missing) and installs all workspace packages
uv sync --all-packages
```

Use commands through uv so they run inside `.venv`:

```bash
uv run uvicorn nam_api.main:app --reload   # see cheat sheet below for worker, etc.
```

**IDE (Cursor / VS Code):** select the interpreter  
`.venv/bin/python` (Command Palette → “Python: Select Interpreter”).

**Optional — activate the venv in your shell:**

```bash
source .venv/bin/activate
```

### Full local setup

```bash
# 1. Install dependencies (+ create .venv)
uv sync --all-packages
# or: uv sync --all-packages

# 2. Configure environment
cp .env.example .env

# 3. Start PostgreSQL (pgvector extension is auto-created on first boot)
docker compose up -d

# 4. Run migrations (once database-schema change adds tables)
uv run --directory packages/db alembic upgrade head

# 5. Start the API
uv run uvicorn nam_api.main:app --reload --host 0.0.0.0 --port 8000

# 6. Start the scheduler worker (separate terminal)
uv run python -m nam_agentic.scheduler.worker
```

### Command cheat sheet (without `just`)

| Task | Command |
|------|---------|
| Sync deps | `uv sync --all-packages` |
| Start DB | `docker compose up -d` |
| Stop DB | `docker compose down` |
| Migrations | `uv run --directory packages/db alembic upgrade head` |
| API | `uv run uvicorn nam_api.main:app --reload --host 0.0.0.0 --port 8000` |
| Worker | `uv run python -m nam_agentic.scheduler.worker` |
| Lint | `uv run ruff check .` |

With [just](https://github.com/casey/just) installed: `just sync`, `just up`, `just api`, etc.

Verify the API: `curl http://localhost:8000/health` → `{"status":"ok"}`

## pgvector

The `vector` extension is created automatically when PostgreSQL starts for the first time via `docker/postgres/init.sql`. No manual `CREATE EXTENSION` step is required.

## Package layout

```text
packages/db/   → nam_db (shared kernel)
agentic/       → nam_agentic (Deep Agents + scheduler)
api/           → nam_api (FastAPI)
```

Dependency direction: `nam-db` ← `nam-agentic` ← `nam-api`

## Alembic

Migrations live in `packages/db/alembic/`. Run from the repo root:

```bash
uv run --directory packages/db alembic upgrade head
# or: uv run --directory packages/db alembic upgrade head
```

Alembic uses the async template and reads `DATABASE_URL` from `nam_db.settings`.

## Development

```bash
just lint    # or: uv run ruff check .
just down    # or: docker compose down
```

## Roadmap

1. `monorepo-architecture` — skeleton (this change)
2. `database-schema` — ORM models + initial migration
3. `deep-agent-core` — working tools + DeepAgentFactory
4. `market-scheduler` — live APScheduler triggers
5. `api-crud` — REST endpoints

See `openspec.md` for the full specification.
