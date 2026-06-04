# AGENTS.md — conventions & notes for coding agents

> Notes for AI assistants working on NAM (Nestor Asset Manager).

## Project shape

```text
packages/db/   nam-db     — SQLAlchemy models, Alembic (single migration history)
api/           nam-api    — user-facing REST (:8000)
agentic/       nam-agentic — always-on agent runtime (:8001)
front/         Next.js UI (:3000) — API consumer only
```

**Backend** (Python / uv): `packages/db`, `api/`, `agentic/` — env at repo root (`.env`).  
**Frontend** (Node / pnpm): `front/` — env in `front/.env` (see `front/.env.example`).

**Dependency graph:** `nam-db` ← `nam-api` and `nam-db` ← `nam-agentic` (siblings).  
**Coupling:** PostgreSQL (shared) + HTTP event bus (`POST /events` on agentic).  
**No Python import** from `nam-api` → `nam-agentic`. Front talks to `nam-api` over HTTP only.

## Commit message convention

Format:

```text
<type>(<module>): <short description in English, imperative mood>
```

### Types

| Type | Use when |
|------|----------|
| `feat` | New capability or endpoint |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `update` | Non-feature refresh (deps, config, tooling) |
| `refacto` | Behaviour-preserving restructure |

Other types (`test`, `chore`, `build`) are OK when they fit better.

### Modules (scope in parentheses)

| Module | Path / scope |
|--------|----------------|
| `agents` | This file, agent-facing instructions |
| `api` | `api/nam_api/` |
| `agent` | `agentic/nam_agentic/` |
| `front` | `front/` (Next.js) |
| `db` | `packages/db/` |
| `openspec` | `openspec.md`, `openspec/` |
| `infra` | `justfile`, `docker/`, root `pyproject.toml`, `.env.example` |

### Examples

```text
feat(agent): add FastAPI event bus and market scheduler
feat(api): add portfolio transactions and positions endpoints
fix(api): reject sell when quantity exceeds position
docs(openspec): document agent runtime architecture
update(infra): run api and agentic in just run back
refacto(db): extract portfolio enums to nam_db.enums
test(api): add position calculator unit tests
```

### Commit hygiene

- **One coherent concern per commit** — do not mix unrelated modules (e.g. API routes + agent scheduler in one commit).
- **Split at file level** when concerns differ; keep each commit buildable when possible.
- **Never commit secrets** (`.env`, credentials). `.env.example` and `.env.test` are fine.
- **Do not commit** unless the user asks.

## Architecture (current)

### nam-api (:8000)

- Singleton user: `POST /setup`, `GET|PUT /profile`
- Portfolio: `/indices`, `/transactions`, `/positions`
- After setup/profile update → fire-and-forget `POST {AGENTIC_URL}/events`
- No auth in v1

### nam-agentic (:8001)

- `GET /health`, `POST /events` (202, async via BackgroundTasks)
- APScheduler in FastAPI **lifespan** — market cron EU/US/ASIA
- `EventHandler` routes events to stub hooks — **hand-owned** implementation

Event types (`agentic/nam_agentic/schemas/events.py`):

- `user.profile.created` / `user.profile.updated`
- `market.session` (cron)
- `chat.message` (future)

### Hand-owned (human implements)

Do **not** auto-implement unless explicitly asked:

- `DeepAgentFactory`, `AgentRunner` wiring in `EventHandler`
- Subagent classes (`agents/`), tools (`tools/`), prompts content
- Writing `USER_GOALS.md` and other workspace files
- WebSocket chat proxy on API

Extension point: `agentic/nam_agentic/services/event_handler.py` → inject `AgentRunner` in each `_on_*` method.

## Tests

```bash
just test          # API suite in Docker (32 tests)
uv run pytest agentic/tests -q
just lint
just back          # Postgres + migrate + api + agentic
just app           # back + Next.js front
just front         # front only (backend must already run)
```

## Code style

- Python ≥ 3.12, uv workspace, ruff (line-length 100)
- OOP for agents/tools; prompts as markdown in `prompts/`
- Domain enums in `nam_db.enums` — not `Literal[...]`
- Minimize scope; match existing patterns; no drive-by refactors

## OpenSpec

- Master reference: `openspec.md`
- Active/completed changes: `openspec/changes/<name>/`
- Completed: `api-portfolio-core`, `agent-runtime-service`
