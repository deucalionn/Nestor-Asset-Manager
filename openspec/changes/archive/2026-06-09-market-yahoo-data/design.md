# Design — market-yahoo-data

## Context

- **Done**: `boursorama-news-tools` — Bourso news cache (`get_financials_news`), live scrape tools, `boursorama_ticker`, `index_type`, ETF vs COMPANY routing.
- **Gap**: No live prices, no history, no structured Yahoo financials; `MarketPriceProvider` is a stub; `GetMarketPriceTool` planned in `openspec.md` §9 but not implemented.
- **User intent**: Yahoo (`yfinance`) for market data; `yahoo_symbol` on `indices` (human + agent, mirroring Bourso); tools suffixed `_from_yf`; Bourso news tool renamed `_from_bourso`; **no** automatic dual-fetch Bourso+Yahoo on every call.
- **Constraints** (from `openspec.md` / `AGENTS.md`):
  - Market data tools live in `nam-agentic` only — no `nam-api` import from agentic
  - OOP tools via `BaseNamTool`; Pydantic v2 schemas; enums in `nam_db.enums`
  - Agents never write financial tables (`indices.yahoo_symbol` is metadata cache, same as `boursorama_ticker`)
  - yfinance calls MUST run off the event loop (`asyncio.to_thread`)

**Separate follow-up change:** Bourso calendar table parser (`calendar_events`) — explicitly out of scope here.

## Goals / Non-Goals

**Goals:**

- Persist optional `yahoo_symbol` on `indices` (API + agent tools)
- DB-first symbol resolution via `YahooIndexResolver` (ISIN or name → Yahoo symbol, auto-persist)
- Live spot price and OHLCV history via yfinance
- Structured company financials (statements + key `.info` fields) on demand — **not** every cycle
- Live ticker news via yfinance — complement to Bourso cache/scrape, not replacement
- Replace stub `MarketPriceProvider` so `get_portfolio_positions` computes PnL when symbol is known
- Rename `get_financials_news` → `get_financials_news_from_bourso` for naming consistency

**Non-Goals:**

- Bourso calendar structured ingest (wrong parser today — future change)
- Cron-ingested price history or Yahoo news cache in PostgreSQL
- nam-api REST endpoints for quotes
- Mapping `boursorama_ticker` → `yahoo_symbol` automatically
- Real-time (sub-minute) quotes or order execution
- Replacing Bourso key figures (`get_data_from_url(key_figures_url)`) — Yahoo financials are **complementary**

## Decisions

### 1. Two providers, two identifier columns

```
indices
├── isin                 → portfolio identity
├── boursorama_ticker    → Bourso news / key figures / ETF composition
└── yahoo_symbol         → Yahoo price / history / financials / news
```

**Rationale:** Different vendors, different symbol namespaces (`1rPAI` ≠ `AI.PA`). Same resolution pattern, independent caches.

### 2. Tool naming: explicit source suffix

| Yahoo tool | Bourso equivalent (existing) |
|------------|-------------------------------|
| `get_financials_news_from_bourso` | (rename from `get_financials_news`) |
| `get_asset_news_from_yf` | `get_data_from_url` (company news live) |
| `get_company_financials_from_yf` | `get_data_from_url` (key_figures_url) |
| `search_yahoo_symbol` | `search_boursorama` |
| `update_index_yahoo_symbol` | `update_index_boursorama` |

**Rationale:** Agent docstrings and prompts disambiguate source without a mega-tool.

### 3. No mandatory dual-fetch

Agents call Bourso news cache **or** Yahoo asset news **or** both **explicitly** per workflow — not fused into one tool that always hits both APIs.

Macro PRE_OPEN: `get_financials_news_from_bourso` (cron-refreshed SQL) + optional `get_data_from_url` for article depth.  
Company analysis: `search_yahoo_symbol` → price/history/financials/news from YF as needed + Bourso news/key figures when FR context matters.

### 4. YahooIndexResolver — DB-first, yfinance Lookup

Resolution order (mirrors `BoursoramaIndexResolver`):

```
resolve(index_id | isin | query)
  ├─ indices.yahoo_symbol IS NOT NULL → return symbol, resolved_from_db=true
  └─ NULL → yfinance Lookup(ISIN or name)
            → filter by index_type (get_stock vs get_etf)
            → prefer Euronext Paris (.PA) for ambiguous EU hits
            → auto-persist yahoo_symbol
            → return symbol, resolved_from_db=false
```

Use **`Lookup`** (not `Search`) for symbol resolution — dedicated ticker lookup endpoint, better for ISIN/name queries. Use **`Search(symbol).news`** only in `get_asset_news_from_yf`.

**Alternative considered:** Derive Yahoo symbol from ISIN via external API — rejected (extra dependency).

### 5. YfinanceMarketPriceProvider

```text
YfinanceMarketPriceProvider
  → resolve yahoo_symbol (index row or resolver)
  → asyncio.to_thread(Ticker(symbol).fast_info / history)
  → Decimal price for get_portfolio_positions
```

`get_asset_price_from_yf` and provider share a thin `YfinanceClient` wrapper (rate-limit logging, error mapping).

### 6. get_company_financials_from_yf

- **COMPANY** `index_type` only — reject ETF
- Returns structured JSON-friendly output: `info` subset + optional statement tables (annual/quarterly) as serializable records
- **On demand only** — no cron; financials change slowly
- Does **not** remove Bourso key figures workflow

### 7. get_asset_history_from_yf

Parameters: `period` (e.g. `1mo`, `6mo`, `1y`, `5y`), optional `interval` (`1d` default).  
Returns: list of `{ date, open, high, low, close, volume }`.

### 8. Subagent wiring

| Subagent | Yahoo tools |
|----------|-------------|
| Macro Strategist | `get_asset_price_from_yf`, `get_asset_history_from_yf`, `get_asset_news_from_yf` |
| Sector Analyst | above + `get_company_financials_from_yf`, `search_yahoo_symbol`, `update_index_yahoo_symbol` |
| ETF Quant | same as Macro (no `get_company_financials_from_yf`) |
| Portfolio Manager | unchanged |

All also keep Bourso tools from prior change (with renamed news tool).

### 9. Package layout

```text
agentic/nam_agentic/tools/services/yahoo/
├── client.py           # asyncio.to_thread wrappers around yfinance
├── resolver.py         # YahooIndexResolver
├── lookup.py           # Lookup query + EU/.PA preference
└── errors.py           # YahooSymbolNotFoundError, etc.
```

Extend `tools/schemas/market.py` (or `yahoo.py`) with Yahoo tool I/O models.

### 10. Settings

Add to `nam_agentic/settings.py` (optional v1):

- `yahoo_resolve_prefer_suffix: str = ".PA"` — PEA/EU default
- `yahoo_request_timeout_sec: int = 30`

## Risks / Trade-offs

- **[Risk] Yahoo unofficial API breaks** → Mitigation: isolate `YfinanceClient`; tests mock yfinance; graceful null in portfolio positions
- **[Risk] Wrong symbol on ambiguous lookup** → Mitigation: prefer `.PA`; if multiple high-confidence hits, error with candidates; manual `update_index_yahoo_symbol`
- **[Risk] EU small-cap sparse financials** → Mitigation: tool returns partial data + clear empty-state message
- **[Risk] Rename breaks prompts/tests** → Mitigation: single rename commit in apply phase; grep all references
- **[Trade-off] No price cache** → acceptable v1 personal use; add DB cache later if rate limits bite
- **[Trade-off] Delayed quotes** → document in tool docstrings; fine for agent briefs

## Migration Plan

1. Alembic: add `indices.yahoo_symbol`
2. Deploy agentic with yfinance dep + stub provider replaced
3. Existing indices: `yahoo_symbol = NULL` — resolver fills on first tool use
4. Rename tool in registry + prompts + tests (same release)
5. Rollback: drop column; revert to stub provider; restore old tool name

## Open Questions

- Whether `get_asset_history_from_yf` should accept raw `yahoo_symbol` without `index_id` — **default: yes** (same pattern as other market tools).
- Max history rows returned — **default: 252** (≈1y daily) cap in tool schema.
