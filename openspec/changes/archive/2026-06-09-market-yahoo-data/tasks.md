## 1. Database schema

- [x] 1.1 Add `yahoo_symbol` (nullable, max 32) to `indices` SQLAlchemy model
- [x] 1.2 Create Alembic migration adding `indices.yahoo_symbol`
- [x] 1.3 Export updated `Index` model from `nam_db` public API

## 2. API indices

- [x] 2.1 Add optional `yahoo_symbol` to `IndexCreate` / `IndexRead` in `nam_api/schemas/index.py`
- [x] 2.2 Update `IndexService` create/list/get to persist and return `yahoo_symbol`
- [x] 2.3 Update API index tests for create/read with and without `yahoo_symbol`

## 3. Yahoo services (agentic)

- [x] 3.1 Add `yfinance` dependency to `agentic/pyproject.toml`
- [x] 3.2 Add Yahoo settings to `nam_agentic/settings.py` (`yahoo_resolve_prefer_suffix`, `yahoo_request_timeout_sec`)
- [x] 3.3 Implement `tools/services/yahoo/errors.py` — typed exceptions
- [x] 3.4 Implement `tools/services/yahoo/client.py` — `asyncio.to_thread` wrapper for Lookup, fast_info, history, info, financials, news
- [x] 3.5 Implement `tools/services/yahoo/lookup.py` — filter by index_type, prefer `.PA`
- [x] 3.6 Implement `tools/services/yahoo/resolver.py` — DB-first `YahooIndexResolver` with auto-persist
- [x] 3.7 Implement `YfinanceMarketPriceProvider` in `tools/services/market_price.py` (keep `StubMarketPriceProvider` + `FakeMarketPriceProvider` for tests)

## 4. Yahoo tool schemas

- [x] 4.1 Extend `nam_agentic/tools/schemas/market.py` with Yahoo tool I/O models
- [x] 4.2 Add `yahoo_symbol` to portfolio schemas (`PositionItem`, `IndexDetailOutput`, `IndexListItem`, `CreateIndexInput`)

## 5. Yahoo market tools

- [x] 5.1 Implement `GetAssetPriceFromYfTool`
- [x] 5.2 Implement `GetAssetHistoryFromYfTool` (252-bar cap)
- [x] 5.3 Implement `GetCompanyFinancialsFromYfTool` — COMPANY only, ETF rejected
- [x] 5.4 Implement `GetAssetNewsFromYfTool` — live ticker news, no SQL cache
- [x] 5.5 Implement `SearchYahooSymbolTool` — Lookup-based, DB-first
- [x] 5.6 Implement `UpdateIndexYahooSymbolTool` — manual override
- [x] 5.7 Write enriched docstrings for all six Yahoo tools

## 6. Bourso news tool rename

- [x] 6.1 Rename `GetFinancialsNewsTool` → `GetFinancialsNewsFromBoursoTool` (module + LangChain name `get_financials_news_from_bourso`)
- [x] 6.2 Update `ToolRegistry` — new name, default `YfinanceMarketPriceProvider`
- [x] 6.3 Update subagent `tools()` lists and all prompt references (`MACRO_STRATEGIST.md`, `SECTOR_ANALYST.md`, `ETF_QUANT.md`)
- [x] 6.4 Update cross-tool docstrings (e.g. `search_past_analyses`) to reference `get_financials_news_from_bourso`

## 7. Subagent wiring

- [x] 7.1 Macro: add `get_asset_price_from_yf`, `get_asset_history_from_yf`, `get_asset_news_from_yf`
- [x] 7.2 Sector: Macro Yahoo set + `get_company_financials_from_yf`, `search_yahoo_symbol`, `update_index_yahoo_symbol`
- [x] 7.3 ETF Quant: Macro Yahoo set only (no company financials)
- [x] 7.4 Update prompts with Yahoo vs Bourso workflow guidance (explicit source choice, no dual-fetch)

## 8. Tests and verification

- [x] 8.1 Unit tests: `YahooIndexResolver` — cache hit, ISIN auto-persist, ambiguous lookup error, `.PA` preference
- [x] 8.2 Unit tests: `YfinanceClient` — mocked yfinance, confirms `asyncio.to_thread` usage
- [x] 8.3 Unit tests: `YfinanceMarketPriceProvider` — price populated / null on failure
- [x] 8.4 Unit tests: each Yahoo tool — happy path + validation errors (mocked client)
- [x] 8.5 Unit tests: `GetCompanyFinancialsFromYfTool` rejects ETF
- [x] 8.6 Unit tests: rename — registry exposes `get_financials_news_from_bourso`, not old name
- [x] 8.7 Integration: `get_portfolio_positions` with `FakeMarketPriceProvider` / mocked yfinance
- [x] 8.8 Verify `just test` and `uv run pytest agentic/tests -q` green
