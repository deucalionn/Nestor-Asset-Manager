## Context

**Done:** `calendar-shared-backend` — `CompositeBackend` with `/shared/` on volume, `market.session` → `AgentRunner.invoke()`, PM + 3 sync subagents via `create_deep_agent`, tools and prompts wired.

**Gap:**

| Area | Today | Target |
|------|-------|--------|
| `user.profile.*` | Log + unused `NamRuntimeContext` | `invoke()` onboarding |
| `chat.message` | Stub | API WS → agentic `/chat/stream` |
| Checkpointer | None | Postgres (all envs) |
| User workspace | Only `/shared/` on disk | `/user/{user_id}/` for `USER_GOALS.md` |
| Agent graph | Built in `AgentRunner.__init__` | Built **once** at lifespan startup; reused for all invocations |
| ToolRegistry | `@lru_cache` + default user | Built once at startup with `default_user_id` (v1 single user) |
| general-purpose | Auto-enabled by Deep Agents | Disabled |
| Front chat | "Coming soon" | Live WS to API |

**Constraints:**

- nam-api MUST NOT import nam-agentic as Python dependency
- Front MUST use a **single origin** (`NEXT_PUBLIC_API_URL`) — chat proxied through API
- Sync subagents only (no `AsyncSubAgent` / Agent Protocol in this change)
- Persistence across app restart: volume for filesystem paths, Postgres for checkpoints

## Goals / Non-Goals

**Goals:**

- Onboarding agent run writes durable workspace files under `/user/`
- Chat with streaming tokens and multi-turn memory via Postgres checkpointer + `thread_id`
- One checkpointer strategy everywhere (Postgres, not MemorySaver in dev)
- Disable `general-purpose` so PM delegates only to `macro-strategist`, `sector-analyst`, `etf-quant`
- API WebSocket proxy to agentic HTTP stream

**Non-Goals:**

- Full Docker Compose stack (front + db + api + agentic) — separate change
- Async subagents (`start_async_task`, etc.)
- `memory=` harness parameter / StoreBackend for AGENTS.md (optional later)
- Auth / multi-tenant RBAC
- Human-in-the-loop `interrupt_on`

## Decisions

### 1. Memory vs backend — what persists across restart

```
┌─────────────────────────────────────────────────────────────┐
│                    PERSISTENCE LAYERS                        │
├─────────────────────┬───────────────────────────────────────┤
│ Volume (Filesystem) │ /shared/calendar/today.md             │
│ agent_workspace_dir │ /user/{user_id}/USER_GOALS.md         │
├─────────────────────┼───────────────────────────────────────┤
│ PostgreSQL          │ news_items, analyses, users, …        │
│ (nam-db)            │ LangGraph checkpoint tables           │
├─────────────────────┼───────────────────────────────────────┤
│ StateBackend        │ Scratch per thread — persisted ONLY   │
│ (default route)     │ when checkpointer saves graph state   │
└─────────────────────┴───────────────────────────────────────┘
```

**Rationale:** User goals and calendar are **files on a mounted volume** — obvious, backup-friendly, survives container restart. Chat history lives in **checkpoint tables** in the same Postgres already used by NAM. No `memory=` parameter in v1 — `PORTFOLIO.md` + `/user/USER_GOALS.md` via `read_file` is enough.

**Alternative considered:** `StoreBackend` + `memory=["/memories/AGENTS.md"]` — rejected for v1; adds LangGraph store setup without clear benefit over `/user/` files.

### 2. Checkpointer — Postgres only

```python
# Single path dev + prod
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

checkpointer = AsyncPostgresSaver.from_conn_string(settings.database_url)
await checkpointer.setup()  # lifespan

create_deep_agent(..., checkpointer=checkpointer)
```

**Rationale:** User rejected dev/prod split. Same `DATABASE_URL` as nam-db. Checkpoint tables are separate from domain tables but same instance.

**Alternative considered:** `MemorySaver` for local — rejected.

### 3. Chat transport — API WebSocket proxy (not `/events`)

```
Front ──WS──► nam-api /ws/chat
                  │
                  │  HTTP POST /chat/stream (chunked NDJSON or SSE)
                  ▼
              nam-agentic
                  │
                  └── AgentRunner.stream(message, context, thread_id)
```

**Rationale:** `POST /events` returns 202 fire-and-forget — correct for `market.session` and profile side-effects, **wrong for chat**. Dedicated streaming endpoint preserves sibling-module isolation while giving the front one URL.

**Wire format (NDJSON over HTTP, relayed on WS):**

```json
{"type": "token", "content": "..."}
{"type": "done", "thread_id": "uuid"}
{"type": "error", "message": "..."}
```

**Alternative considered:** WebSocket directly on agentic — rejected; front would need two origins.

### 4. Sync subagents — keep, parallel within round

PM may call `task(macro-strategist)`, `task(sector-analyst)`, `task(etf-quant)` in parallel in one model turn. Harness runs them concurrently; PM blocks until all return before committee review. No async subagents until chat needs background tasks across user messages.

### 5. Disable general-purpose

Register harness profile with `general_purpose_subagent.enabled=False` so PM cannot delegate to a generic agent instead of NAM experts.

### 6. Process-lifetime compiled graph (no rebuild per invoke)

`nam-agentic` = API classique + un agent chaud derrière. Au lancement du serveur l'agent est compilé ; ensuite il **attend** (idle) jusqu'à un event ou un message chat.

The compiled LangGraph agent is built **once** when the FastAPI app starts — not on every `invoke()` or API call, and **not** lazily on the first cron tick.

```
Lifespan enter
    │
    ├── checkpointer = AsyncPostgresSaver(...); await setup()
    ├── registry = ToolRegistry(session_factory, default_context)
    ├── factory = DeepAgentFactory(..., checkpointer=checkpointer)
    ├── agent_runner = AgentRunner(factory)   # factory.build() once here
    ├── app.state.agent_runner = agent_runner
    └── scheduler.start()                       # only after agent is ready
            │
            yield  →  server accepts /health, /events, /chat/stream
            │
            ▼
    Idle (no LLM) until trigger
            │
    ┌───────┴────────┐
    ▼                ▼
 cron → event    POST /chat/stream
    │                │
    └── agent_runner.invoke/stream(message, context)
            └── same compiled graph; new message + config.thread_id
```

**Rationale:** Rebuilding `create_deep_agent()` per request would re-bind Ollama, tools, and subagents unnecessarily. LangGraph is designed for a long-lived compiled graph; persistence is via **checkpointer + `thread_id`**, not by recreating the graph.

**v1 single user:** `ToolRegistry` is constructed once with `settings.default_user_id`. Event and chat handlers still pass `NamRuntimeContext(user_id=...)` for market/phase/thread — in v1 that `user_id` matches the default. Multi-tenant later would require tools to read `user_id` from runtime context at invoke time (without rebuilding the graph).

Remove misleading `@lru_cache` on `get_agent_runner()` if it blocks injecting the lifespan-built runner — prefer explicit app-state or lifespan wiring over per-request factories.

### 7. Backend layout (extended CompositeBackend)

```python
CompositeBackend(
    default=StateBackend(),
    routes={
        "/shared/": FilesystemBackend(root_dir=workspace / "shared", virtual_mode=True),
        "/user/": FilesystemBackend(root_dir=workspace / "user", virtual_mode=True),
    },
)
```

Agent paths: `/user/{user_id}/USER_GOALS.md` (virtual path maps under `workspace/user/`).

Onboarding seed instructs PM to `write_file` there after `get_user_context`.

### 8. Profile events

| Event | Behavior |
|-------|----------|
| `user.profile.created` | `invoke()` with onboarding seed; async via existing BackgroundTasks |
| `user.profile.updated` | `invoke()` with profile refresh seed; **rewrite** `/user/{user_id}/USER_GOALS.md` from fresh `get_user_context` |
| `chat.message` | **Removed** from `EventType` — chat only via API WS → `/chat/stream` |

`POST /setup` continues to fire `user.profile.created` via HTTP to `/events` (202).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Checkpoint tables grow unbounded | Document retention policy later; thread_id per chat session |
| WS proxy adds latency vs direct agentic | Acceptable for single-user v1; one hop on LAN |
| Ollama slow on first chat token | Stream tokens so UX feels responsive |
| Volume not mounted in naive deploy | Document `agent_workspace` volume; lost files if ephemeral FS |
| Postgres checkpointer setup on shared DB | Use `checkpointer.setup()` in agentic lifespan; separate table prefix |

## Migration Plan

1. Add checkpoint dependency and lifespan `setup()`
2. Extend backend `/user/` route
3. Wire profile `invoke()` handlers
4. Add `/chat/stream` on agentic + tests with mock LLM
5. Implement API WS proxy
6. Enable front chat page
7. Update `.env.example` with any new vars
8. Run `just test` + manual WS smoke test

Rollback: revert agentic/api/front changes; checkpoint tables harmless if unused.

### 9. Market session `thread_id`

Format: `market:{market}:{phase}:{date}` (e.g. `market:EU:PRE_OPEN:2026-06-09`).

Deterministic per cron firing; distinct from chat UUIDs; checkpoint state for market cycles does not overwrite chat threads.

## Open Questions

- Docker Compose full stack — **deferred** to next change (volume + network implications for memory persistence)
