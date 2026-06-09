## 1. Event-driven agent wiring

- [x] 1.1 Construct `AgentRunner(DeepAgentFactory(...))` in `dependencies.py` and inject into `EventHandler`
- [x] 1.2 Wire `EventHandler._on_market_session` to `AgentRunner.invoke()` with `NamRuntimeContext(market, phase)` and a minimal cycle seed message
- [x] 1.3 Add smoke test: `market.session` event triggers `invoke` (mock agent or spy)

## 2. Shared backend

- [x] 2.1 Add `nam_agentic/backends/shared.py` with `build_agent_backend()` (`CompositeBackend`: `StateBackend` + `/shared/` → `FilesystemBackend`, `virtual_mode=True`)
- [x] 2.2 Wire `DeepAgentFactory.build()` to pass `backend=build_agent_backend()`
- [x] 2.3 Ensure `{agent_workspace_dir}/shared` is created on startup (extend `EventHandler` or main lifespan)
- [x] 2.4 Add `data/agent_workspace/` to `.gitignore`; document `AGENT_WORKSPACE_DIR` in `.env.example`

## 3. Calendar parser and fetch tool

- [x] 3.1 Capture HTML fixtures from Bourso calendar pages (at least `CALENDAR_MACRO` + one other) under `agentic_tests/fixtures/boursorama/`
- [x] 3.2 Rename `DAILY_FEEDS` → `CALENDAR_FEEDS` in `feeds.py`; remove calendar from `NewsIngestService` daily path
- [x] 3.3 Implement `calendar_parser.py` against fixtures
- [x] 3.4 Add Pydantic schemas: `FetchCalendarFromBoursoInput/Output`, `CalendarSectionOutput`, `CalendarEventRow`
- [x] 3.5 Implement `FetchCalendarFromBoursoTool` — HTTP via `BoursoramaHttpClient`, returns markdown only
- [x] 3.6 Register tool on `ToolRegistry`; wire on `PortfolioManagerAgent` only

## 4. Remove daily calendar SQL ingest

- [x] 4.1 Remove `news.ingest.daily` scheduler job from `register_news_ingest_jobs`
- [x] 4.2 Remove `EventType.NEWS_INGEST_DAILY` handler and `ingest_daily()` from active ingest path
- [x] 4.3 Update ingest tests: session feeds unchanged; no daily calendar upsert expectations

## 5. Prompts

- [x] 5.1 Update `PORTFOLIO.md`: at session start, refresh calendar if `/shared/calendar/today.md` missing or `_fetched_at` ≠ today (`fetch_calendar_from_bourso` → `write_file`)
- [x] 5.2 Update `MACRO_STRATEGIST.md`, `SECTOR_ANALYST.md`, `ETF_QUANT.md`: prefer `read_file("/shared/calendar/today.md")` at session start; flag stale/missing file; no `CALENDAR_*` SQL as primary source
- [x] 5.3 Verify subagent tool lists exclude `fetch_calendar_from_bourso`

## 6. Tests and verification

- [x] 6.1 Unit tests for `calendar_parser` (fixtures, empty/malformed HTML)
- [x] 6.2 Unit/integration test for `FetchCalendarFromBoursoTool` (mock HTTP, no DB writes)
- [x] 6.3 Test `build_agent_backend()` path mapping
- [x] 6.4 Run `uv run pytest agentic/tests -q` and `just test`; fix regressions

## 7. Infra (when compose exists)

- [x] 7.1 Document or add Docker volume mount for `agent_workspace_dir` in dev compose / justfile comments
