# Nestor Asset Manager (NAM)

I invest in the stock market but don't have time to track my portfolio and the markets every day. NAM is a personal assistant that does that for me: it watches market sessions (EU, US, Asia), analyzes my positions, keeps a memory of its analyses, and suggests recommendations — without ever placing orders on my behalf. I always have the final say; Nestor assists.

Technically: **backend** monorepo (Python / uv) + **frontend** (Next.js). Local stack via Docker Compose; **Ollama stays on the host machine**.

First run: `just app` → `http://localhost:3000` (onboarding, portfolio, chat).

### Backend (Python)

- **nam-db** — shared SQLAlchemy models, enums, Alembic migrations
- **nam-agentic** — always-on agent runtime (FastAPI), Deep Agents, Postgres checkpointer, APScheduler market jobs
- **nam-api** — user-facing FastAPI REST + WebSocket chat proxy (`/ws/chat` → agentic `/chat/stream`)

### Frontend (Node)

- **front/** — Next.js + TypeScript, consumes nam-api only (`NEXT_PUBLIC_API_URL`)

## Architecture (v1)

```text
Browser ──HTTP/WS──► nam-api (:8000)          Ollama (:11434, host)
                        │                              ▲
                        └── WS /ws/chat ──► agentic (:8001) ── HTTP ──► LLM
                              │
                              ├── POST /events (202)
                              └── POST /chat/stream

Docker Compose: db (pgvector) + migrate + api + agentic + front
PostgreSQL — domain tables + pgvector + LangGraph checkpoint tables
data/agent_workspace/ — shared calendar + USER_GOALS.md (mounted volume)
```

Chat is **not** on the event bus: the front never talks to agentic directly.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose v2
- [Ollama](https://ollama.com/) on the **host** — `ollama serve` + `ollama pull gemma4`
- [just](https://github.com/casey/just) — optional shortcuts (`brew install just`)

For lint/tests or debugging outside Docker: Python ≥ 3.12, [uv](https://docs.astral.sh/uv/), Node ≥ 20, pnpm.

## Quick start

```bash
cp .env.example .env
ollama pull gemma4          # once
just app                    # db + migrate + api + agentic + front
```

Open `http://localhost:3000`. `Ctrl+C` stops the stack; `just down` removes containers.

| Command | What runs |
|---------|-----------|
| `just app` | Full stack in Docker (with hot-reload on bind mounts) |
| `just back` | db + api + agentic only (no front) |
| `just down` | Stop and remove containers |
| `just down-v` | Same + delete Postgres volume |
| `just logs` | Follow compose logs |
| `just test` | CI-style pytest in Docker (`nam_test`) |
| `just lint` | ruff (local uv) |

**Ollama** is not in Compose: agentic calls `http://host.docker.internal:11434` (macOS / Docker Desktop; Linux via `host-gateway` in compose).

## Local development (without Docker)

Useful for IDE integration, debugging a single service, or fast pytest runs:

```bash
uv sync --all-packages
cp .env.example .env
just up && just migrate    # Postgres only in Docker
just api                   # or just agentic / just front
```

## pgvector

The `vector` extension is created automatically when PostgreSQL starts for the first time via `docker/postgres/init.sql`. Embeddings use Ollama (`nomic-embed-text`), stored as `vector(384)`.

## Package layout

```text
packages/db/   → nam_db
api/           → nam_api
agentic/       → nam_agentic
front/         → Next.js UI
docker/        → Dockerfiles (python, front)
```

**Backend:** `nam-db` ← `nam-api` and `nam-db` ← `nam-agentic` (HTTP siblings).  
**Frontend:** `front/` → HTTP/WS → `nam-api` only.

## Tests

```bash
just test        # migrate + pytest api/tests agentic/agentic_tests
just test-down
```

Agent conventions: `AGENTS.md`. Full specification: `openspec.md`.
