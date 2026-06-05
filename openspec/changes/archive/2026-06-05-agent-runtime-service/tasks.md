# Tasks — agent runtime service

Scope: **skeleton only** — agent/subagent/tool implementation is hand-owned (see `openspec.md` §6–9 for follow-up work).

## Specs

- [x] Update `openspec.md` §2–3, §5–7 — agentic FastAPI, HTTP events, remove worker
- [x] Add change docs under `openspec/changes/agent-runtime-service/`
- [x] Add `specs/agent-runtime/spec.md`

## Agentic FastAPI

- [x] `nam_agentic/main.py` — lifespan, scheduler start/stop
- [x] `routers/health.py`, `routers/events.py`
- [x] `schemas/events.py`, `services/event_handler.py` (stub hooks)
- [x] `scheduler/scheduler.py` — register market cron jobs
- [x] Delete `scheduler/worker.py`
- [x] Settings: `agentic_host`, `agentic_port`, `agent_workspace_dir`
- [x] Add `fastapi`, `uvicorn` to agentic deps

## nam-api integration

- [x] `services/agentic_client.py` — fire-and-forget `POST /events`
- [x] Emit events on `POST /setup` and `PUT /profile`
- [x] Remove `nam-agentic` from api dependencies; add `httpx`

## Dev infra

- [x] `justfile` — `agentic` command; `just back` / `just app` run api + agentic
- [x] `.env.example` — `AGENTIC_URL`, agent bind vars

## Tests

- [x] `agentic/tests/test_runtime.py` — health + events
- [x] `just test` — 32 API tests green
