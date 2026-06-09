## Why

Agents and portfolio views need **live market data** (spot price, history, structured financials, ticker news) but NAM only has a stub `MarketPriceProvider` returning null. Bourso covers **news and key figures** via scrape; **quotes and Yahoo-native data** need a separate provider. PEA instruments are keyed by ISIN in `indices` — Yahoo requires a **symbol cache** (`AI.PA`, `CW8.PA`) with the same DB-first resolution pattern as `boursorama_ticker`.

## What Changes

- Add `indices.yahoo_symbol` (nullable, max 32) — set by user (API) or agent (auto-resolve + manual override)
- Implement **yfinance** stack in `nam-agentic`: resolver, price provider, async client wrapper
- Add agent tools (explicit `_from_yf` suffix):
  - `get_asset_price_from_yf`
  - `get_asset_history_from_yf`
  - `get_company_financials_from_yf` (COMPANY only; on demand, no cron)
  - `get_asset_news_from_yf` (live ticker news; on demand)
  - `search_yahoo_symbol` (DB-first via `YahooIndexResolver`)
  - `update_index_yahoo_symbol` (manual override)
- Wire `YfinanceMarketPriceProvider` into `GetPortfolioPositionsTool` (replace stub)
- **Rename** `get_financials_news` → `get_financials_news_from_bourso` for source clarity (registry, prompts, tests)
- Extend API + portfolio tools schemas with optional `yahoo_symbol`
- Subagent wiring: Macro/Sector/ETF get price + history + asset news; Sector adds financials + yahoo search

**Non-breaking** for API — additive field on index create/read.

**Out of scope (this change):** Bourso structured calendar parser (`calendar_events` table), nam-api REST price endpoints, price history DB cache/cron, combining Bourso + Yahoo news in one automatic fetch.

## Capabilities

### New Capabilities

- `yahoo-symbol-schema`: `indices.yahoo_symbol` column + Alembic migration
- `yahoo-market-provider`: yfinance client, `YahooIndexResolver`, `YfinanceMarketPriceProvider`
- `agentic-yahoo-tools`: Six Yahoo tools + Pydantic schemas + docstrings
- `bourso-news-tool-rename`: Rename `get_financials_news` → `get_financials_news_from_bourso`

### Modified Capabilities

- `api-indices`: optional `yahoo_symbol` on `IndexCreate` / `IndexRead`
- `agentic-package`: ToolRegistry expansion, subagent wiring, portfolio tool schema updates

## Impact

| Area | Impact |
|------|--------|
| `packages/db/` | `indices.yahoo_symbol`; migration |
| `api/nam_api/` | `IndexCreate` / `IndexRead` + optional `yahoo_symbol` |
| `agentic/` | `tools/market/`, `tools/services/yahoo/`, `MarketPriceProvider` impl |
| Dependencies | `yfinance` in `agentic/pyproject.toml` |
| External | Yahoo Finance (unofficial API via yfinance) |
| Tests | Mock yfinance; no live Yahoo in CI |
