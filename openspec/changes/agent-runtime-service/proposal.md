# Agent runtime service

## Why

The agent must run **always-on**, separate from the user-facing API. Market observation and onboarding runs belong in `nam-agentic`, not in a standalone worker stub or in-process imports from `nam-api`.

## What changes

- **`nam-agentic`** becomes a **FastAPI app** (`:8001`) with `GET /health`, `POST /events`, and APScheduler registered in the app **lifespan**
- **Remove** `scheduler/worker.py` — no separate worker process
- **`nam-api`** notifies agentic via HTTP (`AGENTIC_URL`) after profile setup/update; **no Python import** of `nam-agentic`
- Market cron jobs fire internal `market.session` events → `EventHandler` → (future) `AgentRunner`

## Architecture

```text
nam-api (:8000)  ──POST /events──►  nam-agentic (:8001)
       │                                    │
       └──────── PostgreSQL ◄── tools ──────┘
                    agent workspace volume (USER_GOALS.md written by agent)
```

## Non-goals (this change)

- Deep Agent graph, subagents, tools — **hand-implemented by project owner**
- `EventHandler` → `AgentRunner` wiring
- WebSocket chat proxy from API to agentic
- Docker Compose production layout for agentic (local `just dev` first)
