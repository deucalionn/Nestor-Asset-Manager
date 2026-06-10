# AGENTS.md — conventions & notes for coding agents

> Notes for AI assistants working on NAM (Nestor Asset Manager).

## Project shape

```text
packages/db/    nam-db      — SQLAlchemy models, Alembic (single migration history)
packages/yahoo/ nam-yahoo   — Yahoo Finance client, resolver, market pricing
api/            nam-api     — user-facing REST (:8000)
agentic/        nam-agentic — always-on agent runtime (:8001)
front/          Next.js UI (:3000) — API consumer only
```

**Backend** (Python / uv): `packages/db`, `packages/yahoo`, `api/`, `agentic/` — env at repo root (`.env`).  
**Frontend** (Node / pnpm): `front/` — env in `front/.env` (see `front/.env.example`).

**Dependency graph:** `nam-db` ← `nam-yahoo` ← `nam-api` and `nam-db` ← `nam-yahoo` ← `nam-agentic` (siblings).  
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
| `yahoo` | `packages/yahoo/` |
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
- Chat: `WS /ws/chat` → HTTP stream proxy to agentic `POST /chat/stream`
- Chat threads (metadata): `GET/POST /chat/threads`, `PATCH/DELETE /chat/threads/{id}`, `GET /chat/threads/{id}/messages` (history proxied to agentic)
- No auth in v1

### nam-agentic (:8001)

- `GET /health`, `POST /events` (202, async via BackgroundTasks)
- `POST /chat/stream` — NDJSON chat stream (tokens, status, done, error); every event carries `thread_id`
- `GET /chat/threads/{thread_id}/messages` — checkpoint history for a LangGraph thread
- APScheduler in FastAPI **lifespan** — market cron EU/US/ASIA
- Compiled Deep Agent built **once** at startup (Postgres checkpointer by default)
- `EventHandler` routes events → `AgentRunner.invoke()` for market + profile lifecycle

Event types (`agentic/nam_agentic/schemas/events.py`):

- `user.profile.created` / `user.profile.updated` → onboarding / refresh seeds
- `market.session` (cron)
- `news.ingest.session` (cron, no agent invoke)

Chat is **not** on the event bus — front → API WebSocket → agentic `/chat/stream`.  
One **conversation = one LangGraph `thread_id`**; sidebar lists thread metadata from API (`chat_threads` table). Message bodies live in the Postgres checkpointer.

### Hand-owned (human implements)

Do **not** auto-implement unless explicitly asked:

- Subagent classes (`agents/`), tools (`tools/`), prompts content
- Prompt prose in `prompts/` (`PORTFOLIO.md`, subagent `.md` files)
- Tuning agent behaviour (committee flow, recommendation policy)

Wiring (`DeepAgentFactory`, `AgentRunner`, checkpointer, chat proxy, chat threads REST) is **implemented** — extend via `event_handler.py` seeds and agent/tool classes.

**Chat vs cron:** same Portfolio Manager agent and `PORTFOLIO.md`. Chat passes the raw user message; scheduled events pass a seed message. No separate `CHAT.md` prompt.

## Tests

```bash
just app           # Docker: db + migrate + api + agentic + front (Ollama on host)
just back          # Docker: backend only
just test          # API + agentic tests in Docker
just lint          # ruff (local uv)
just api           # single service, local uv (debug)
just agentic       # single service, local uv (debug)
just front         # Next.js only, local pnpm (backend must run)
```

## Code style

- Python ≥ 3.12, uv workspace, ruff (line-length 100)
- OOP for agents/tools; prompts as markdown in `prompts/`
- Domain enums in `nam_db.enums` — not `Literal[...]`
- Minimize scope; match existing patterns; no drive-by refactors

## OpenSpec

- Master reference: `openspec.md`
- Active/completed changes: `openspec/changes/<name>/`
- Completed: `api-portfolio-core`, `agent-runtime-service`, …
- In progress: `chat-v2-conversations` (multi-thread chat, single PM prompt, sidebar)
