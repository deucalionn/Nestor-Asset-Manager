## Why

The Deep Agent graph, subagents, tools, and calendar shared backend exist, but **runtime wiring is incomplete**: profile and chat events are stubs, there is no LangGraph checkpointer, onboarding does not materialize workspace files, and chat has no streaming path. Users cannot converse with Nestor or complete agent-driven onboarding after `POST /setup`.

This change makes agents **actually runnable end-to-end** while preserving module isolation (nam-api and nam-agentic as HTTP siblings).

## What Changes

- Wire `user.profile.created` and `user.profile.updated` to `AgentRunner.invoke()` with onboarding seeds
- Add `/user/` filesystem route so the PM writes `USER_GOALS.md` and related files that **survive process restarts** (volume-backed)
- Add **PostgreSQL LangGraph checkpointer** (same database as nam-db, dev and prod — no in-memory split)
- Pass stable `thread_id` on chat invocations; persist conversation state across turns and restarts
- Disable Deep Agents built-in `general-purpose` subagent (PM must delegate only to NAM experts)
- Build the compiled Deep Agent **once per process** at startup (lifespan); each event or chat request calls `invoke()` / `stream()` on the live graph — no graph rebuild per request
- Add `POST /chat/stream` on nam-agentic (streaming response, not `POST /events`)
- Implement **WebSocket chat proxy** on nam-api: front connects only to API; API streams to/from agentic
- Enable functional chat in the front app shell (remove "coming soon")
- Keep **sync subagents** (`task()` tool) — parallel delegation within a round, no async subagents in this change

**Out of scope (follow-up):** full-stack Docker Compose deployment (db + api + agentic + front containers) — discussed separately.

## Capabilities

### New Capabilities

- `agent-checkpointer`: PostgreSQL LangGraph checkpointer shared across environments
- `agent-chat-stream`: nam-agentic streaming chat endpoint and runner integration
- `api-chat-proxy`: nam-api WebSocket endpoint proxying to agentic stream

### Modified Capabilities

- `agent-runtime`: Profile/chat event invoke wiring; chat uses dedicated stream endpoint not `/events`
- `agent-shared-backend`: Add `/user/` volume route for per-user workspace files
- `agentic-package`: Disable general-purpose subagent; process-lifetime graph + checkpointer wiring; `thread_id` on runner
- `api-package`: Replace WebSocket stub with chat proxy; HTTP-only coupling to agentic (no Python import)
- `front-app-shell`: Enable navigable functional chat UI

## Impact

- **agentic/**: `factory.py`, `runner.py`, `dependencies.py`, `event_handler.py`, `backends/shared.py`, new chat router, settings, pyproject deps (`langgraph-checkpoint-postgres` or equivalent)
- **api/**: `websocket/chat.py`, HTTP client to agentic, env `AGENTIC_URL`
- **front/**: chat page, WebSocket client to API
- **packages/db/**: optional migration or init for checkpoint tables (if not auto-created by LangGraph)
- **infra**: `.env.example`, volume mount docs for `agent_workspace_dir` (persistence across restart)
- **openspec.md**: update chat flow diagram (WS proxy, not in-process AgentRunner)
