# Design — calendar-shared-backend

## Context

- **Done**: `boursorama-news-tools` — `NewsIngestService`, `DAILY_FEEDS` (four calendar URLs), `news.ingest.daily` at 07:00, `get_financials_news_from_bourso` with `CALENDAR_*` categories, `AGENT_WORKSPACE_DIR` setting.
- **Done**: `agent-runtime-service` — FastAPI + APScheduler always-on; cron enqueues `market.session` and `news.ingest.*` events; `EventHandler` routes by type; `AgentRunner` + `DeepAgentFactory` exist but **`invoke()` is not wired yet**.
- **Gap**: Calendar list pages use table HTML; `list_parser` treats them as headline feeds → useless rows in `news_items`. Macro strategist prompts still point agents at `CALENDAR_*` SQL cache.
- **Done (skeleton)**: `DeepAgentFactory` calls `create_deep_agent()` with **no** `backend` → default `StateBackend()` (ephemeral, not shared on disk).
- **User intent**: No calendar cron. Service waits for events; agent wakes per event. PM owns calendar fetch; one file per day overwritten; subagents read via native filesystem tools when prompts say so (prefer session start); files on Docker volume, not in repo.

## Goals / Non-Goals

**Goals:**

- Clarify and wire the **event-driven agent model** (`market.session` / chat → `AgentRunner` → PM)
- Persist today's calendar as markdown at `/shared/calendar/today.md` on a volume-backed filesystem backend
- Share the same backend instance across PM and all subagents (`read_file` / `write_file` native)
- Parse Bourso calendar tables from the four existing URLs
- PM refreshes calendar during agent runs when `_fetched_at` is stale (prompt: prefer EU session start)
- Remove redundant SQL ingest path for calendars; keep session MARKETS/FINANCE cron (**no LLM**)

**Non-Goals:**

- Dedicated APScheduler job or cron for calendar
- `ReadCalendarTool` or any custom filesystem read tool
- `calendar_events` table or Alembic migration
- Calendar history (no dated archive files)
- Embedding or pgvector for calendar content
- Storing calendar files in git
- Playwright / JS rendering
- Continuous LLM loop — agent only runs when an event fires

## Decisions

### 0. Always-on service vs agent wake (runtime model)

```
nam-agentic process (always running while `just back`)
├── FastAPI :8001          ← POST /events (chat, profile, manual)
├── APScheduler            ← cron → events
│     ├── market.session   ──► EventHandler ──► AgentRunner.invoke()  ← LLM
│     └── news.ingest.session ──► EventHandler ──► NewsIngestService  ← NO LLM
└── between events: idle (no LLM tokens)
```

**Rationale:** Matches NAM architecture from `agent-runtime-service`. Calendar refresh lives in the **LLM path** (`market.session`), not a third cron. Headlines stay on the **I/O path** (`news.ingest.session`).

**Alternative considered:** Calendar cron at 07:00 → rejected (wrong parser historically + duplicates agent fetch).

### 1. Shared file vs PostgreSQL for same-day calendar

```
market.session (e.g. EU PRE_OPEN cron)
      │
      ▼
EventHandler._on_market_session
      │
      ▼
AgentRunner.invoke(cycle brief, NamRuntimeContext)
      │
      ▼
PM Deep Agent  (prompt: refresh calendar if stale)
      │
      ├─ fetch_calendar_from_bourso  → markdown
      ├─ write_file("/shared/calendar/today.md", ...)   ← native
      └─ task → Macro Strategist (when PM delegates)
              └─ read_file("/shared/calendar/today.md")   ← native, when needed
```

Between runs, `/shared/calendar/today.md` **persists on the volume** — subagents in a later event can still read it without re-fetching.

**Rationale:** Calendar is **working memory**, not domain memory in PostgreSQL.

### 2. CompositeBackend layout

```python
CompositeBackend(
    default=StateBackend(),
    routes={
        "/shared/": FilesystemBackend(
            root_dir=settings.agent_workspace_dir / "shared",
            virtual_mode=True,
        ),
    },
)
```

| Path prefix | Backend | Persistence |
|-------------|---------|-------------|
| `/shared/` | `FilesystemBackend` on `{AGENT_WORKSPACE_DIR}/shared` | Docker volume / local `data/` (gitignored) |
| everything else | `StateBackend` | Ephemeral per run |

Physical file: `{AGENT_WORKSPACE_DIR}/shared/calendar/today.md`  
Agent path: `/shared/calendar/today.md`

**Alternative considered:** `StoreBackend` → deferred; volume filesystem is enough for v1 shared calendar.

### 3. Fetch tool returns content; PM writes via native `write_file`

`FetchCalendarFromBoursoTool` returns markdown only — no filesystem or SQL writes.

PM prompt: after fetch, `write_file` to `/shared/calendar/today.md` if `_fetched_at` date ≠ today (or file missing).

**Rationale:** Shared-state writes stay visible in agent trace; domain tool stays HTTP-only.

### 4. No custom read tool; prompt-guided access

Subagents use `read_file("/shared/calendar/today.md")` when their task needs calendar context. Prompts **prefer** reading at session start — not a code-enforced ordering.

Subagent prompts: if `_fetched_at` is missing or not today's date, note staleness in analysis or ask PM to refresh — do not fall back to `CALENDAR_*` SQL.

### 5. Ingest cron: remove daily only, keep session (no LLM)

| Job | LLM? | After this change |
|-----|------|-------------------|
| `news.ingest.daily` | No | **Removed** (was calendar → SQL) |
| `news.ingest.session` | No | **Unchanged** (MARKETS + FINANCE → SQL) |
| `market.session` | Yes | **Unchanged** (triggers PM run → calendar file) |

Rename `DAILY_FEEDS` → `CALENDAR_FEEDS` (URLs kept for fetch tool).

### 6. Calendar markdown format

```markdown
# Market calendar — 2026-06-09 (Europe/Paris)

_fetched_at: 2026-06-09T07:20:00+02:00_

## CALENDAR_MACRO
| Time | Event | Previous | Last | Importance |
...
```

### 7. Docker / dev persistence

`AGENT_WORKSPACE_DIR=./data/agent_workspace` — gitignored, volume-mounted in Docker.

### 8. EventHandler → AgentRunner wiring (in scope)

`dependencies.py` constructs `AgentRunner(DeepAgentFactory(...))` and injects into `EventHandler`.

`_on_market_session` MUST call `AgentRunner.invoke()` with a cycle brief derived from `market` + `phase` and `NamRuntimeContext`.

Profile and chat handlers MAY call `invoke()` with appropriate prompts (minimal stub message acceptable in v1 if graph is wired).

This wiring is **required** for calendar refresh — there is no other trigger.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| PM forgets `write_file` after fetch | Strong PM prompt; tool output reminds to persist markdown |
| Stale `today.md` if no session runs | PM prompt: check `_fetched_at`; subagents flag stale header |
| Bourso HTML layout change | HTML fixtures + parser tests; partial sections OK |
| Two-step fetch + write fragile | Accepted trade-off for traceability |
| `AgentRunner` wiring delayed | Explicit task in this change — calendar blocked without it |

## Migration Plan

1. Wire `EventHandler` → `AgentRunner` on `market.session`
2. Deploy backend + fetch tool + parser
3. Update prompts
4. Remove daily ingest cron/handler
5. First `market.session` run populates `/shared/calendar/today.md`

**Rollback:** Re-enable daily ingest from git history; keep AgentRunner wiring.

## Open Questions

- `_on_market_session` invoke message template — hand-owned in PM prompt + minimal seed message in handler (e.g. `"EU PRE_OPEN cycle"`).
- `virtual_mode=True` — verify with installed deepagents version during implementation.
