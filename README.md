# Nestor Asset Manager (NAM)

Autonomous financial decision-support platform built as a uv monorepo with three Python packages:

- **nam-db** — shared SQLAlchemy models, enums, Alembic migrations
- **nam-agentic** — always-on agent runtime (FastAPI), Deep Agents, APScheduler market jobs
- **nam-api** — user-facing FastAPI REST (WebSocket chat deferred)

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
uv run uvicorn nam_api.main:app --reload   # see cheat sheet below for agentic, etc.
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

# 5–6. Start API + agent runtime (or: just dev)
uv run uvicorn nam_api.main:app --reload --host 0.0.0.0 --port 8000
uv run uvicorn nam_agentic.main:app --reload --host 0.0.0.0 --port 8001
```

### Command cheat sheet (without `just`)

| Task | Command |
|------|---------|
| Sync deps | `uv sync --all-packages` |
| Start DB | `docker compose up -d` |
| Stop DB | `docker compose down` |
| Migrations | `uv run --directory packages/db alembic upgrade head` |
| Tests (API, all) | `just test` |
| API | `uv run uvicorn nam_api.main:app --reload --host 0.0.0.0 --port 8000` |
| Agent runtime | `uv run uvicorn nam_agentic.main:app --reload --host 0.0.0.0 --port 8001` |
| Lint | `uv run ruff check .` |

With [just](https://github.com/casey/just) installed: `just sync`, `just dev`, `just api`, etc.

**Full local stack:** `just dev` starts Postgres (Docker), runs migrations, then API + agent runtime in parallel. `Ctrl+C` stops both apps; run `just down` to stop the DB.

Verify: `curl http://localhost:8000/health` and `curl http://localhost:8001/health`

First-run setup (once):

```bash
curl -X POST http://localhost:8000/setup \
  -H 'Content-Type: application/json' \
  -d '{"firstname":"Lucas","date_of_birth":"1990-01-15","strategy":"BALANCED","goals":"Retire early"}'
```

Then portfolio routes work without `user_id` in the URL: `/transactions`, `/positions`. The agent uses `DEFAULT_USER_ID` from `.env` — set it to match the profile `id` returned by `/setup` if you want a stable UUID.

## pgvector

The `vector` extension is created automatically when PostgreSQL starts for the first time via `docker/postgres/init.sql`. No manual `CREATE EXTENSION` step is required.

## Package layout

```text
packages/db/   → nam_db (shared kernel)
agentic/       → nam_agentic (FastAPI agent runtime + Deep Agents)
api/           → nam_api (user REST API)
```

Dependency direction: `nam-db` ← `nam-api` and `nam-db` ← `nam-agentic` (sibling services; API notifies agentic via HTTP)

## Alembic

Migrations live in `packages/db/alembic/`. Run from the repo root:

```bash
uv run --directory packages/db alembic upgrade head
# or: uv run --directory packages/db alembic upgrade head
```

Alembic uses the async template and reads `DATABASE_URL` from `nam_db.settings`.

## Tests

All API tests (unit + services + routes) run in Docker against PostgreSQL (pgvector):

```bash
just test        # alembic upgrade head + pytest api/tests
just test-down   # tear down test containers and volumes
```

One command — no separate local pytest for portfolio tests.

The test-runner applies Alembic migrations once, then each test truncates portfolio tables (schema stays, data is reset).

## Development

```bash
just lint    # or: uv run ruff check .
just down    # or: docker compose down
```

## Roadmap

1. `monorepo-architecture` — skeleton ✓
2. `api-portfolio-core` — portfolio CRUD + Docker tests ✓
3. `agent-runtime-service` — agentic FastAPI + event bus + scheduler ✓
4. **Deep agent (hand-owned)** — wire `EventHandler` → `AgentRunner`, implement agents/subagents/tools
5. **Chat proxy (optional)** — API WebSocket → `chat.message` events

See `openspec.md` for the full specification.
