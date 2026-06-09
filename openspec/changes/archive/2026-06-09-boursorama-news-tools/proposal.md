## Why

Autonomous market briefs (PRE_OPEN, PERIODIC, CLOSE) and subagent analyses need **fresh financial news, macro calendars, and company context** — but agents today have no news tools (`GetFinancialsNewsTool`, `GetDataFromUrlTool` are planned in `openspec.md` §9 and explicitly marked unavailable in subagent prompts).

Relying on live scraping inside every agent cycle would be slow, fragile, and redundant. NAM needs a **Boursorama-first news pipeline**: scheduled background ingestion into PostgreSQL, plus on-demand tools so agents can search and deep-read specific pages when the cache is not enough.

PEA portfolios are **ETF-heavy**: trackers have no company news page on Bourso. Instrument type (`COMPANY` vs `ETF`) must drive which URLs and tools agents use.

## What Changes

- Add PostgreSQL schema for ingested news/calendar entries (`news_items` table + enums)
- Extend `indices` with:
  - optional `boursorama_ticker` — user or agent (DB-first resolution)
  - required `index_type` enum (`COMPANY` | `ETF`) — drives URL patterns and tool eligibility
- Implement a **Boursorama scraper service** (`httpx` + `selectolax` parsing + `trafilatura` + LLM formatting)
- Register **APScheduler ingest jobs** in `nam-agentic` lifespan (calendriers 1×/day, marchés/finances 3×/EU session)
- Add agent tools:
  - `GetFinancialsNewsTool` — query cached `news_items`
  - `GetDataFromUrlTool` — whitelisted URLs; company news index / articles / key figures / global hub
  - `SearchBoursoramaTool` — DB-first ticker resolution; **type-aware** canonical URLs
  - `GetEtfCompositionTool` — parse tracker composition page (holdings + weights)
  - `UpdateIndexBoursoramaTool` — manual ticker override only (auto-persist is default path)
- Wire tools onto subagents; add `get_index` + `get_portfolio_positions` to Sector + ETF for DB-first workflows
- Enrich **all** tool docstrings (existing + new) — multi-line `Use when` / `Do not use when` / `Returns` (no `get_tools` meta-tool)
- Add `news.ingest.*` event handlers (no LLM)

**Deferred (v1):** `GetCompanyFinancialsTool` from `openspec.md` §9 — covered by `key_figures_url` + `get_data_from_url` for `COMPANY` indices.

**Non-breaking** for nam-api — additive fields on index create/read only.

## Capabilities

### New Capabilities

- `news-ingestion-schema`: `news_items`, `indices.boursorama_ticker`, `indices.index_type`, enums
- `boursorama-news-ingestion`: Scheduled fetch, HTTP client, ingest handlers
- `agentic-news-tools`: News, URL, search, ETF composition, ticker update tools

### Modified Capabilities

- `agent-runtime`: news ingest cron + `news.ingest.*` events
- `agentic-package`: ToolRegistry + subagent wiring (news tools + portfolio read tools on Sector/ETF)
- `api-indices`: optional `boursorama_ticker`, required `index_type` on create/read

## Impact

| Area | Impact |
|------|--------|
| `packages/db/` | `news_items`; `indices.boursorama_ticker`, `indices.index_type`; migration |
| `api/nam_api/` | `IndexCreate` / `IndexRead` + `index_type`, optional `boursorama_ticker` |
| `agentic/` | `tools/market/`, `tools/services/boursorama/`, scheduler, event handlers |
| Dependencies | `httpx`, `trafilatura`, `selectolax` |
| External | `www.boursorama.com` + `bourse.boursobank.com` (tracker pages) — polite HTTP client |
| Tests | HTML fixtures; ETF vs COMPANY routing tests |

**Out of scope:** price quotes, Playwright, Google search, nam-api news REST, per-ETF news pages (do not exist on Bourso). News embeddings are **in scope** (see design §5).
