# Nestor Asset Manager (NAM)

J’investis en bourse, mais je n’ai pas le temps de suivre mon portefeuille et les marchés au quotidien. NAM est un assistant personnel qui s’en charge à ma place : il observe les séances (EU, US, Asie), analyse mes positions, garde une mémoire de ses analyses, et me propose des recommandations — sans jamais exécuter d’ordres à ma place. Je garde le dernier mot ; Nestor m’accompagne.

Techniquement : monorepo **backend** (Python / uv) + **frontend** (Next.js). Stack locale via Docker Compose ; **Ollama reste sur la machine hôte**.

Premier usage : `just app` → `http://localhost:3000` (onboarding, portefeuille, chat).

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
data/agent_workspace/ — calendar partagé + USER_GOALS.md (volume monté)
```

Chat is **not** on the event bus: the front never talks to agentic directly.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose v2
- [Ollama](https://ollama.com/) on the **host** — `ollama serve` + `ollama pull gemma4`
- [just](https://github.com/casey/just) — optional shortcuts (`brew install just`)

For lint/tests or debug hors Docker : Python ≥ 3.12, [uv](https://docs.astral.sh/uv/), Node ≥ 20, pnpm.

## Quick start

```bash
cp .env.example .env
ollama pull gemma4          # once
just app                    # db + migrate + api + agentic + front
```

Open `http://localhost:3000`. `Ctrl+C` stops the stack ; `just down` removes containers.

| Command | What runs |
|---------|-----------|
| `just app` | Full stack in Docker (with hot-reload on bind mounts) |
| `just back` | db + api + agentic only (no front) |
| `just down` | Stop and remove containers |
| `just down-v` | Same + delete Postgres volume |
| `just logs` | Follow compose logs |
| `just test` | CI-style pytest in Docker (`nam_test`) |
| `just lint` | ruff (local uv) |

**Ollama** n’est pas dans Compose : l’agentic appelle `http://host.docker.internal:11434` (macOS / Docker Desktop ; Linux via `host-gateway` dans le compose).

## Local development (without Docker)

Utile pour l’IDE, le debug d’un seul service, ou pytest rapide :

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
