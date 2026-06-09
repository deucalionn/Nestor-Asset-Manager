## Requirements

### Requirement: Calendar feed URL configuration
`nam_agentic/tools/services/boursorama/feeds.py` MUST define `CALENDAR_FEEDS: tuple[IngestFeed, ...]` with the four Boursorama calendar URLs and matching `NewsCategory` values:

| Path suffix | Category |
|-------------|----------|
| `/bourse/actualites/calendriers/` | `CALENDAR_GENERAL` |
| `/bourse/actualites/calendriers/societes-cotees` | `CALENDAR_LISTED_COMPANIES` |
| `/bourse/actualites/calendriers/macroeconomique` | `CALENDAR_MACRO` |
| `/bourse/actualites/calendriers/dividendes` | `CALENDAR_DIVIDENDS` |

These URLs MUST be used by `FetchCalendarFromBoursoTool` only — not by SQL ingest cron or any APScheduler job.

Calendar fetch MUST occur inside agent runs (typically when `EventHandler` handles `market.session` and invokes `AgentRunner`), not on a standalone schedule.

#### Scenario: Feed config reused by fetch tool
- **WHEN** `FetchCalendarFromBoursoTool` runs
- **THEN** it iterates all four `CALENDAR_FEEDS` entries
- **AND** each fetch uses the configured `IngestFeed.url`

### Requirement: Calendar table parser
`nam_agentic/tools/services/boursorama/calendar_parser.py` MUST parse Boursorama calendar **table** HTML (not headline list layout) into structured rows.

Each parsed row MUST expose:

| Field | Type | Notes |
|-------|------|-------|
| `time` | str \| None | Local time label (e.g. `10:00`) |
| `event` | str | Event title |
| `previous` | str \| None | Prior reading |
| `last` | str \| None | Latest reading |
| `importance` | int \| None | Star/importance level when present |

#### Scenario: HTML fixtures exist before parser ship
- **WHEN** `calendar_parser` tests run in CI
- **THEN** frozen HTML fixtures under `agentic_tests/fixtures/boursorama/` cover at least `CALENDAR_MACRO` and one other calendar category
- **AND** fixtures are derived from real Boursorama calendar table pages (not headline list pages)

#### Scenario: Macro calendar fixture parses table rows
- **WHEN** `calendar_parser` receives HTML from a saved `CALENDAR_MACRO` fixture
- **THEN** at least one row is returned with non-empty `event`
- **AND** rows are not produced by reusing `list_parser` headline heuristics

#### Scenario: Empty or malformed section is non-fatal
- **WHEN** one calendar URL returns HTTP 500 or unparsable HTML
- **THEN** the parser returns an empty list for that section
- **AND** other sections still parse
- **AND** the tool completes without raising to the agent

### Requirement: FetchCalendarFromBourso Pydantic schemas
`nam_agentic/tools/schemas/market.py` MUST define:

**FetchCalendarFromBoursoInput**: empty or optional `include_categories: list[NewsCategory] | None` (default all four).

**CalendarSectionOutput**: `category: NewsCategory`, `rows: list[CalendarEventRow]`, `source_url: str`.

**CalendarEventRow**: `time`, `event`, `previous`, `last`, `importance` (matching parser fields).

**FetchCalendarFromBoursoOutput**: `markdown: str`, `fetched_at: datetime`, `sections: list[CalendarSectionOutput]`.

#### Scenario: Output includes combined markdown
- **WHEN** the tool succeeds for at least one feed
- **THEN** `markdown` is non-empty
- **AND** includes a top-level date heading and `_fetched_at` metadata line
- **AND** includes one `## {NewsCategory}` section per parsed feed

### Requirement: FetchCalendarFromBoursoTool
`FetchCalendarFromBoursoTool` MUST:

1. Fetch calendar pages via shared `BoursoramaHttpClient` (sequential, jittered — same discipline as ingest)
2. Parse with `calendar_parser`
3. Render combined markdown
4. Return `FetchCalendarFromBoursoOutput` — **MUST NOT** write to filesystem or PostgreSQL

LangChain tool name: `fetch_calendar_from_bourso`.

#### Scenario: Tool does not persist to news_items
- **WHEN** `fetch_calendar_from_bourso` completes successfully
- **THEN** no new or updated rows are written to `news_items`
- **AND** no embedding is computed

#### Scenario: HTTP goes through shared client
- **WHEN** the tool fetches two calendar URLs in one invocation
- **THEN** both requests use `BoursoramaHttpClient`
- **AND** requests are sequential with jitter between them

### Requirement: Canonical shared calendar path
The canonical agent path for today's calendar MUST be `/shared/calendar/today.md`.

Content MUST be overwritten on each refresh (no dated archive files, no history retention in `/shared/calendar/`).

#### Scenario: PM overwrites same path on refresh
- **WHEN** PM refreshes the calendar on two consecutive session runs
- **THEN** both writes target `/shared/calendar/today.md`
- **AND** the second write replaces the first file contents entirely

### Requirement: Portfolio Manager calendar workflow
`PortfolioManagerAgent` MUST expose `fetch_calendar_from_bourso` in `tools()`.

`PORTFOLIO.md` MUST instruct the PM that at **session start** (preferably EU `PRE_OPEN` or first cycle of the day) and when preparing macro work:

1. Check `/shared/calendar/today.md` — if missing or `_fetched_at` is not today's date (`Europe/Paris`), refresh
2. Call `fetch_calendar_from_bourso`, then native `write_file` with path `/shared/calendar/today.md` and the returned `markdown`
3. If the file is already fresh for today, skip fetch and proceed with the cycle

Prompt guidance MUST NOT require a dedicated calendar cron — refresh happens during agent runs triggered by `market.session` (or user chat when applicable).

#### Scenario: PM has fetch tool, subagents do not
- **WHEN** `PortfolioManagerAgent.tools()` is reviewed
- **THEN** `fetch_calendar_from_bourso` is present
- **WHEN** `MacroStrategistAgent.tools()` is reviewed
- **THEN** `fetch_calendar_from_bourso` is absent

### Requirement: Subagent prompt calendar source
`MACRO_STRATEGIST.md`, `SECTOR_ANALYST.md`, and `ETF_QUANT.md` MUST direct agents to read `/shared/calendar/today.md` via native `read_file` for calendar context — **preferably at session start** when the task involves macro timing or scheduled events.

They MUST NOT instruct using `get_financials_news_from_bourso` with `CALENDAR_*` categories as the primary calendar source.

If `_fetched_at` is missing or not today's date, the agent SHOULD note staleness in its output rather than silently trusting the file or querying legacy `CALENDAR_*` SQL rows.

#### Scenario: Macro prompt references shared path
- **WHEN** `MACRO_STRATEGIST.md` is reviewed
- **THEN** it mentions `/shared/calendar/today.md`
- **AND** it does not list `CALENDAR_MACRO` as the primary calendar workflow

#### Scenario: Subagent reads on demand via native backend
- **WHEN** a subagent needs calendar context during its task
- **THEN** it uses native `read_file` on `/shared/calendar/today.md`
- **AND** no custom calendar read tool is invoked
