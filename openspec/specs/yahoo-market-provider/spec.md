## Requirements
### Requirement: yfinance dependency
`agentic/pyproject.toml` MUST declare `yfinance` as a runtime dependency.

#### Scenario: Package installs yfinance
- **WHEN** `uv sync` runs in `agentic/`
- **THEN** `yfinance` is importable in the agentic environment

### Requirement: YfinanceClient async wrapper
`nam_agentic/tools/services/yahoo/client.py` MUST wrap all yfinance I/O with `asyncio.to_thread` so the FastAPI event loop is never blocked.

The client MUST expose async methods for at least:

| Method | yfinance surface |
|--------|------------------|
| `lookup(query: str)` | `Lookup` |
| `get_fast_info(symbol: str)` | `Ticker(symbol).fast_info` |
| `get_history(symbol, period, interval)` | `Ticker(symbol).history(...)` |
| `get_info(symbol: str)` | `Ticker(symbol).info` |
| `get_financials(symbol, statement, freq)` | `Ticker(symbol).financials` / `quarterly_financials` / etc. |
| `get_news(symbol: str, count: int)` | `Search(symbol).news` |

Errors from yfinance MUST map to typed exceptions in `errors.py` (e.g. `YahooSymbolNotFoundError`, `YahooDataUnavailableError`).

#### Scenario: Price fetch runs off event loop
- **WHEN** `YfinanceClient.get_fast_info("AI.PA")` is awaited
- **THEN** the underlying sync call executes via `asyncio.to_thread`
- **AND** the caller receives a dict-like fast_info result or a typed error

### Requirement: YahooIndexResolver DB-first resolution
`nam_agentic/tools/services/yahoo/resolver.py` MUST implement resolution order:

1. Load `indices` by `index_id` or `isin`; if `yahoo_symbol` is set → return symbol, `resolved_from_db=true`
2. On cache miss → `Lookup(ISIN or name)` via `YfinanceClient`
3. Filter candidates by `index_type` when known (`get_stock` vs ETF-equivalent)
4. Prefer Euronext Paris suffix `.PA` when multiple EU candidates match (configurable via settings)
5. Auto-persist `yahoo_symbol` on the matching `indices` row
6. Return symbol, `resolved_from_db=false`

`UpdateIndexYahooSymbolTool` is for **manual override only** — not the nominal persist path.

#### Scenario: Cache hit by index_id
- **WHEN** resolver is called with `index_id` and `yahoo_symbol` already in DB
- **THEN** `resolved_from_db=true` and no yfinance Lookup request

#### Scenario: ISIN lookup auto-persist
- **WHEN** resolver is called with `isin` for a row with `yahoo_symbol=NULL`
- **AND** Lookup returns a single high-confidence `.PA` equity match
- **THEN** `indices.yahoo_symbol` is updated
- **AND** the resolved symbol is returned with `resolved_from_db=false`

#### Scenario: Ambiguous lookup fails clearly
- **WHEN** Lookup returns multiple equally valid symbols with no `.PA` preference
- **THEN** resolver raises `YahooSymbolNotFoundError` with candidate symbols in the message
- **AND** no row is auto-persisted

### Requirement: MarketPriceProvider yfinance implementation
`YfinanceMarketPriceProvider` MUST implement `MarketPriceProvider`:

```python
async def get_price(self, isin: str) -> Decimal | None
```

Resolution flow:

1. Load `indices` row by `isin`
2. Resolve `yahoo_symbol` via `YahooIndexResolver` when null
3. Fetch spot price from yfinance fast_info (e.g. `last_price` or equivalent)
4. Return `Decimal` price or `None` on missing symbol / unavailable quote

`ToolRegistry` MUST inject `YfinanceMarketPriceProvider` by default (replacing `StubMarketPriceProvider`).

Tests MUST use `FakeMarketPriceProvider` or mocked `YfinanceClient` — no live Yahoo in CI.

#### Scenario: Portfolio positions get live price
- **WHEN** `get_portfolio_positions` runs for a position whose index has resolvable `yahoo_symbol`
- **AND** yfinance returns a valid last price
- **THEN** `current_price`, `market_value`, `unrealized_pnl`, and `gain_loss_pct` are populated

#### Scenario: Unresolvable symbol returns null price
- **WHEN** `get_price` is called for an ISIN with no resolvable Yahoo symbol
- **THEN** the method returns `None`
- **AND** `get_portfolio_positions` sets `all_prices_available=false` for that position

### Requirement: Agentic Yahoo settings
`nam_agentic/settings.py` MUST add optional settings:

| Setting | Default |
|---------|---------|
| `yahoo_resolve_prefer_suffix` | `".PA"` |
| `yahoo_request_timeout_sec` | `30` |

#### Scenario: Settings load from env
- **WHEN** agentic app starts with default `.env`
- **THEN** Yahoo settings load without error
