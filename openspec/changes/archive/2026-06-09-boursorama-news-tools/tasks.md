## 1. Database schema

- [x] 1.1 Add `NewsSource`, `NewsCategory`, and `IndexType` to `nam_db.enums`
- [x] 1.2 Add `NewsItem` SQLAlchemy model in `packages/db/nam_db/models/`
- [x] 1.3 Add `boursorama_ticker` (nullable) and `index_type` (NOT NULL, default COMPANY) to `indices` model
- [x] 1.4 Create Alembic migration: `news_items` + `indices` columns + enums
- [x] 1.5 Export new models/enums from `nam_db` public API

## 2. Boursorama scraper services

- [x] 2.1 Add agentic deps: `httpx`, `trafilatura`, `selectolax`
- [x] 2.2 Implement `BoursoramaHttpClient` — singleton, browser headers, Semaphore(1), jitter, budgets, hosts `www.boursorama.com` + `bourse.boursobank.com`
- [x] 2.3 Implement `list_parser.py` — ingest feeds + global `/bourse/actualites/` hub
- [x] 2.3b Implement `company_news_parser.py` — COMPANY `/cours/actualites/{ticker}/` only
- [x] 2.3c Implement `etf_composition_parser.py` — `/bourse/trackers/cours/composition/{ticker}/`
- [x] 2.3d Implement `page_reader.py` — route by URL pattern and `index_type` guards
- [x] 2.4 Implement `search.py` + `BoursoramaIndexResolver` — DB-first, type-aware URLs, auto-persist
- [x] 2.5 Implement `page_formatter.py` + `prompts/PAGE_FORMATTER.md`
- [x] 2.6 Implement `NewsIngestService` — fetch feeds, upsert `news_items`
- [x] 2.7 Add HTML fixtures: ingest feeds, company news index, ETF composition, global hub

## 3. Scheduler and event handlers

- [x] 3.1 Add `news.ingest.daily` and `news.ingest.session` event types
- [x] 3.2 Register daily cron (07:00 Paris) and three EU session crons
- [x] 3.3 Add `EventHandler` ingest handlers (no AgentRunner)
- [x] 3.4 Add static feed URL → category configuration

## 4. API indices

- [x] 4.1 Add `index_type` (required) and optional `boursorama_ticker` to `IndexCreate` / `IndexRead` and service
- [x] 4.2 Update API index tests for COMPANY and ETF create/read

## 5. Portfolio tool extensions

- [x] 5.1 Extend portfolio schemas — `index_type` + `boursorama_ticker` on index/position outputs
- [x] 5.2 Extend `CreateIndexTool`, `GetIndexTool`, `ListIndicesTool` for `index_type` + optional ticker

## 6. Agent market tools

- [x] 6.1 Add `nam_agentic/tools/schemas/market.py`
- [x] 6.2 Implement `GetFinancialsNewsTool`
- [x] 6.3 Implement `GetDataFromUrlTool` — routing, ETF company-news guard, global hub
- [x] 6.4 Implement `SearchBoursoramaTool` — type-aware URLs
- [x] 6.5 Implement `GetEtfCompositionTool` — ETF only
- [x] 6.6 Implement `UpdateIndexBoursoramaTool` — manual override
- [x] 6.7 Extend `ToolRegistry.all_tools()` with five market tools

## 7. Enriched tool docstrings

- [x] 7.1 Document docstring template in `agentic/nam_agentic/tools/base.py` module docstring or `AGENTS.md` pointer
- [x] 7.2 Upgrade docstrings: all 8 basics-tools (`memory/` + `portfolio/`)
- [x] 7.3 Write enriched docstrings for all 5 market tools at implementation time
- [x] 7.4 Test: each bound tool `description` contains `Use when:` and `Returns:` (light assertion in registry test)

## 8. Subagent wiring and prompts

- [x] 8.1 Macro: `get_financials_news`, `get_data_from_url`
- [x] 8.2 Sector: Macro set + `search_boursorama`, `update_index_boursorama`, `get_index`, `get_portfolio_positions`
- [x] 8.3 ETF Quant: Sector set + `get_etf_composition`
- [x] 8.4 Update prompts §5 — align tool list with wired tools; COMPANY vs ETF workflows (docstrings remain source of truth for semantics)
- [x] 8.5 PM unchanged (no URL/search tools)

## 9. Tests and verification

- [x] 9.1 Unit tests: list parser (ingest + global hub fixtures)
- [x] 9.2 Unit tests: `company_news_parser`, `etf_composition_parser`
- [x] 9.3 Unit tests: `PageContentFormatter` + `GetDataFromUrlTool` routing; ETF company-news rejection
- [x] 9.4 Unit tests: `BoursoramaHttpClient` — sequential, jitter, caps, both hosts
- [x] 9.5 Unit tests: `BoursoramaIndexResolver` — COMPANY vs ETF URLs; cache hit/miss
- [x] 9.6 Unit tests: `GetEtfCompositionTool` — ETF ok, COMPANY rejected
- [x] 9.7 Integration: `NewsIngestService` upsert idempotency
- [x] 9.8 Verify `just test` and `uv run pytest agentic/tests -q` green

## 10. Settings and ops

- [x] 10.1 Settings: ingest enabled, jitter min/max, req/min, req/hour, user-agent, LLM format flags
- [x] 10.2 Log ingest metrics: run_id, URLs, rows upserted, errors

## 11. News persist and semantic search

- [x] 11.1 Migration: `news_items.content_embedding` + HNSW index
- [x] 11.2 `NewsItemStore` — upsert with embed; preserve `content_markdown` on headline refresh
- [x] 11.3 `GetDataFromUrlTool` — `persist=true` default on articles; upsert to `news_items`
- [x] 11.4 `GetFinancialsNewsTool` — `semantic_query` + pgvector search
- [x] 11.5 Cron ingest embeds title+summary on upsert
- [x] 11.6 Tests: persist idempotency, semantic search, markdown preserved on re-ingest
