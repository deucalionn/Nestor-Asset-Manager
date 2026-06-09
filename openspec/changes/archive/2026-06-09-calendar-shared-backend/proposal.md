## Why

Boursorama calendar pages are ingested daily into `news_items` via `list_parser`, which expects headline-list HTML — not the structured calendar tables (HEURE / ÉVÈNEMENT / Précédent / Dernier). Agents therefore get poor macro calendar context from SQL cache and embeddings, which is overkill for **same-day ephemeral data**.

The Portfolio Manager should refresh calendars **inside agent runs** triggered by the existing event bus (`market.session` cron, future `chat.message`) — not by a dedicated calendar cron. The PM writes a single shared markdown file on the Deep Agent filesystem backend (Docker volume, not git); all agents read it with native `read_file` when their prompts say to (preferably at session start).

## What Changes

- Document the **event-driven runtime model**: `nam-agentic` is always-on (FastAPI + APScheduler); the LLM agent **wakes on each event** (`market.session`, `chat.message`, profile events) via `EventHandler` → `AgentRunner.invoke()` — no continuous agent loop, no calendar-specific cron
- Wire `EventHandler._on_market_session` (and stub hooks for chat/profile) to `AgentRunner` — prerequisite for calendar refresh and all autonomous cycles
- Wire `DeepAgentFactory` with `CompositeBackend`: ephemeral `StateBackend` default + `/shared/` routed to `FilesystemBackend` on `AGENT_WORKSPACE_DIR` (runtime volume)
- Add `calendar_parser.py` — structured table parser for the four Bourso calendar URLs (reuse existing URL config + HTML fixtures)
- Add `FetchCalendarFromBoursoTool` (PM only) — live scrape + parse → returns combined markdown; PM persists via native `write_file("/shared/calendar/today.md", ...)`
- Prompts: PM refreshes calendar at **session start when stale**; subagents **prefer** reading `/shared/calendar/today.md` each morning/session — prompt-guided, not hard orchestration
- Stop writing calendar data to `news_items` — remove `news.ingest.daily` cron and handler (`news.ingest.session` for MARKETS/FINANCE stays **LLM-free**)
- Keep the four calendar URLs in `CALENDAR_FEEDS` (fetch tool only)
- `.gitignore` / Docker volume for `data/agent_workspace/` — never committed

**Out of scope:** `calendar_events` PostgreSQL table, calendar history, calendar embeddings, nam-api REST, custom read/write filesystem tools, dedicated APScheduler job for calendar.

## Capabilities

### New Capabilities

- `agent-shared-backend`: CompositeBackend wiring, `/shared/` volume paths, Docker persistence
- `bourso-calendar-shared-file`: Calendar table parser, fetch tool, markdown file format, PM/subagent prompt workflow

### Modified Capabilities

- `agent-runtime`: Event-driven agent activation; `AgentRunner.invoke()` wired from `EventHandler` on `market.session` (and extension points for chat/profile)
- `agentic-package`: `DeepAgentFactory` passes shared backend to `create_deep_agent`; PM gets calendar fetch tool
- `boursorama-news-ingestion`: Remove daily calendar SQL ingest and `news.ingest.daily` schedule; retain session feeds only (no LLM)
- `agentic-news-tools`: Deprecate `CALENDAR_*` categories for `get_financials_news_from_bourso` in agent workflows (MARKETS/FINANCE only)

## Impact

| Area | Impact |
|------|--------|
| `agentic/nam_agentic/services/event_handler.py` | `AgentRunner.invoke()` on `market.session` |
| `agentic/nam_agentic/dependencies.py` | Inject `AgentRunner` into `EventHandler` |
| `agentic/nam_agentic/factory.py` | `CompositeBackend` + volume root |
| `agentic/nam_agentic/tools/services/boursorama/` | `calendar_parser.py`; `CALENDAR_FEEDS`; ingest split |
| `agentic/nam_agentic/tools/market/` | `FetchCalendarFromBoursoTool` |
| `agentic/nam_agentic/scheduler/` | Remove daily news ingest job only |
| `agentic/nam_agentic/prompts/` | PM + Macro/ETF/Sector — calendar via `/shared/calendar/today.md` |
| `agentic/nam_agentic/agents/` | PM tool wiring |
| Infra | Docker volume mount for `AGENT_WORKSPACE_DIR`; `.gitignore` entry |
| Tests | Calendar HTML fixtures; parser tests; backend path tests; event → runner smoke test |
| `packages/db/` | No schema change; existing `CALENDAR_*` rows may remain stale (optional cleanup out of scope) |
