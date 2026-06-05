# Design — agent runtime service

## FastAPI lifespan + scheduler

APScheduler `AsyncIOScheduler` starts in `nam_agentic.main.lifespan` and shuts down on app teardown. Market jobs are registered from `MARKET_SESSIONS` via `register_market_jobs()`.

Each cron trigger enqueues a `market.session` event handled by `EventHandler` (background task pattern same as HTTP `/events`).

## Event bus

| Event type | Source | Handler (v1) |
|------------|--------|--------------|
| `user.profile.created` | `POST /setup` in nam-api | Log + stub onboarding context |
| `user.profile.updated` | `PUT /profile` in nam-api | Log + stub refresh |
| `chat.message` | Future WS proxy | Stub |
| `market.session` | APScheduler | Log + stub market context |

HTTP contract: `POST /events` → `202 Accepted`, processing async via FastAPI `BackgroundTasks`.

## Extension points (hand-owned)

The skeleton stops at `EventHandler`. To implement the agent yourself:

```text
POST /events ──► EventHandler.handle()
                      │
        ┌─────────────┼─────────────┬──────────────┐
        ▼             ▼             ▼              ▼
 _on_user_profile  _on_user_profile  _on_chat   _on_market_session
     _created         _updated      _message
        │             │             │              │
        └─────────────┴─────────────┴──────────────┘
                              │
                              ▼
                    AgentRunner.invoke() / stream()
                              │
                              ▼
                    DeepAgentFactory.build()
                              │
                    agents/ + tools/ + prompts/
```

Existing stubs (no behaviour yet): `factory.py`, `runner.py`, `agents/*`, `tools/*`, `prompts/*`.
Wire your logic inside `EventHandler` methods or inject `AgentRunner` via `dependencies.py`.

## Dependency graph (updated)

```text
packages/db  ◄───  api
     ▲
     └──────────  agentic

api ──HTTP──► agentic   (no import edge)
```

## Workspace

`AGENT_WORKSPACE_DIR` (default `./data/agent_workspace`) is owned by the agent process. The API never writes markdown goals files.

## Settings

| Variable | Package | Purpose |
|----------|---------|---------|
| `AGENTIC_URL` | nam-api | Base URL for event notifications |
| `AGENTIC_HOST` / `AGENTIC_PORT` | nam-agentic | Uvicorn bind |
| `AGENT_WORKSPACE_DIR` | nam-agentic | Agent filesystem root |
| `MARKET_TIMEZONE` | nam-agentic | Cron timezone |
