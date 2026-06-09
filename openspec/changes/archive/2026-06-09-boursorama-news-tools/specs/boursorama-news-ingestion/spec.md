## ADDED Requirements

### Requirement: Boursorama list feed configuration
`nam-agentic` MUST define a static configuration mapping ingest jobs to source URLs and categories:

| Job | URLs (path suffix under `https://www.boursorama.com`) | Category |
|-----|------------------------------------------------------|----------|
| daily | `/bourse/actualites/calendriers/` | `CALENDAR_GENERAL` |
| daily | `/bourse/actualites/calendriers/societes-cotees` | `CALENDAR_LISTED_COMPANIES` |
| daily | `/bourse/actualites/calendriers/macroeconomique` | `CALENDAR_MACRO` |
| daily | `/bourse/actualites/calendriers/dividendes` | `CALENDAR_DIVIDENDS` |
| session | `/bourse/actualites/marches/` | `MARKETS` |
| session | `/bourse/actualites/finances/` | `FINANCE` |

#### Scenario: Daily job covers four calendar pages
- **WHEN** `news.ingest.daily` runs successfully
- **THEN** all four daily URLs are fetched
- **AND** at least one `news_items` row per page is inserted or updated when the page contains entries

### Requirement: Daily ingest schedule
APScheduler MUST register a cron job `news.ingest.daily` at **07:00 Europe/Paris** every day.

#### Scenario: Daily cron fires
- **WHEN** the clock reaches 07:00 Europe/Paris on a weekday
- **THEN** a `news.ingest.daily` event is enqueued
- **AND** `EventHandler` runs ingest without invoking `AgentRunner`

### Requirement: Session ingest schedule
APScheduler MUST register `news.ingest.session` for market **EU** at three phases aligned with `MarketSession` (Europe/Paris):

| Phase | Time | Feeds |
|-------|------|-------|
| POST_OPEN | 09:20 | MARKETS + FINANCE |
| PERIODIC (first mid-session) | 13:20 | MARKETS + FINANCE |
| CLOSE | 17:30 | MARKETS + FINANCE |

#### Scenario: Session ingest at EU open
- **WHEN** EU POST_OPEN triggers at 09:20
- **THEN** `news.ingest.session` runs with `market=EU`
- **AND** both session URLs are fetched and upserted

### Requirement: NewsIngestService
`nam_agentic` MUST implement `NewsIngestService` that:

1. Fetches list HTML via `httpx` (async)
2. Parses entries with a dedicated list parser (title, link, optional summary/date)
3. Normalizes relative URLs to absolute `https://www.boursorama.com/...`
4. Upserts rows into `news_items` by `source_url`
5. Sets `fetched_at` to UTC now and assigns a shared `ingest_run_id` per batch

#### Scenario: Successful list parse
- **WHEN** ingest fetches a valid Boursorama list page fixture
- **THEN** at least one `news_items` row is persisted with matching `category`
- **AND** each `source_url` is under `www.boursorama.com`

#### Scenario: Parse failure is non-fatal
- **WHEN** one daily URL returns HTTP 500 or yields zero parseable entries
- **THEN** ingest logs an error for that URL
- **AND** other URLs in the same batch still process
- **AND** the process does not crash the agentic service

### Requirement: BoursoramaHttpClient browser-like configuration
All outbound HTTP to Bourso hosts (ingest cron **and** agent tools) MUST go through a shared singleton `BoursoramaHttpClient`. Direct `httpx` calls bypassing this client are forbidden.

Allowed hosts (after redirects):

| Host | Use |
|------|-----|
| `www.boursorama.com` | News ingest, company pages, global hub |
| `bourse.boursobank.com` | ETF tracker quote + composition pages |

The client MUST send browser-realistic default headers:

| Header | Value |
|--------|-------|
| `User-Agent` | Recent desktop Chrome on macOS (configurable, default constant string) |
| `Accept` | `text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8` |
| `Accept-Language` | `fr-FR,fr;q=0.9,en;q=0.8` |
| `Accept-Encoding` | `gzip, deflate, br` |
| `Connection` | `keep-alive` |
| `Upgrade-Insecure-Requests` | `1` |

Optional `Referer: https://www.boursorama.com/` on deep fetches (article URLs) when enabled by settings.

Client MUST configure: connect timeout 10s, read timeout 30s, `follow_redirects=true` with post-redirect host whitelist check.

#### Scenario: Shared client across ingest and tools
- **WHEN** `NewsIngestService` and `GetDataFromUrlTool` fetch Boursorama in the same process
- **THEN** both use the same `BoursoramaHttpClient` instance and the same rate-limit state

### Requirement: Sequential fetch with random jitter
The client MUST enforce **strictly sequential** requests to allowed Bourso hosts — no parallel/concurrent fetches (`max_concurrent=1`).

Before **every** request, the client MUST `await asyncio.sleep(random.uniform(min_delay, max_delay))` where defaults are:

| Setting | Default |
|---------|---------|
| `boursorama_min_delay_seconds` | `1.5` |
| `boursorama_max_delay_seconds` | `4.0` |

Ingest batches and agent tool calls MUST iterate URLs one-by-one through this client — never `asyncio.gather` on multiple Boursorama URLs.

#### Scenario: Random delay between requests
- **WHEN** two consecutive Boursorama fetches are issued through the client
- **THEN** the second request starts only after the first completes
- **AND** a sleep duration between `min_delay` and `max_delay` elapsed before the second request starts

#### Scenario: Daily ingest is not a burst
- **WHEN** daily ingest fetches four pages in one batch
- **THEN** requests are sequential with jitter between each
- **AND** total elapsed time is at least `4 * min_delay` seconds

### Requirement: Request budget caps
The client MUST enforce rolling budgets to prevent burst traffic:

| Setting | Default | Scope |
|---------|---------|-------|
| `boursorama_max_requests_per_minute` | `12` | all Boursorama HTTP via shared client |
| `boursorama_max_requests_per_hour` | `120` | all Boursorama HTTP via shared client |

When a budget is exceeded, the client MUST raise `BoursoramaRateLimitError` with a clear message — callers MUST NOT retry immediately (no tight retry loop).

#### Scenario: Per-minute cap blocks burst
- **WHEN** 12 requests were made in the last 60 seconds
- **AND** a 13th request is attempted
- **THEN** `BoursoramaRateLimitError` is raised before any HTTP call

### Requirement: Agent deep-fetch discipline
Agent-facing tools MUST NOT encourage bulk URL fetching:

- `GetDataFromUrlTool` accepts **exactly one URL** per invocation (already single-url input)
- Subagent prompts MUST instruct: after `news_index`, deep-read **at most 3** `article_url` items per analysis task
- `SearchBoursoramaTool` performs **at most one** HTTP search per call (DB cache hit = zero HTTP)

`PageContentFormatter` and `company_news_parser` MUST NOT prefetch linked `article_url` values automatically — the agent chooses which articles to deepen.

#### Scenario: News index does not follow article links
- **WHEN** `get_data_from_url` parses a company news index with 20 headlines
- **THEN** exactly **one** HTTP request is made (the index page)
- **AND** no automatic fetch of `article_url` links occurs

### Requirement: Ingest event types
`nam_agentic/schemas/events.py` MUST add:

| Type | Payload |
|------|---------|
| `news.ingest.daily` | `{}` |
| `news.ingest.session` | `{market: Market}` |

`EventHandler` MUST route these to dedicated async handlers that call `NewsIngestService` only.

#### Scenario: Manual ingest via event bus
- **WHEN** `POST /events` receives `type=news.ingest.daily`
- **THEN** response status is 202
- **AND** ingest runs asynchronously
