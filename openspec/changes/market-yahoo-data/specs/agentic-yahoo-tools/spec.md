## ADDED Requirements

### Requirement: Yahoo market Pydantic schemas
`nam_agentic/tools/schemas/market.py` (or `yahoo.py`) MUST define schemas for all Yahoo tools.

**GetAssetPriceFromYfInput**: exactly one of `index_id: UUID | None`, `isin: str | None`, `yahoo_symbol: str | None` (validator enforced)

**GetAssetPriceFromYfOutput**: `yahoo_symbol`, `currency`, `last_price: Decimal | None`, `previous_close: Decimal | None`, `fetched_at`, `resolved_from_db: bool`

**GetAssetHistoryFromYfInput**: same identity fields as price + `period: str` (default `1y`, allowed: `1mo`, `3mo`, `6mo`, `1y`, `5y`, `max`) + optional `interval: str` (default `1d`)

**HistoryBar**: `date`, `open`, `high`, `low`, `close`, `volume`

**GetAssetHistoryFromYfOutput**: `yahoo_symbol`, `period`, `interval`, `bars: list[HistoryBar]`, `count: int`, `resolved_from_db: bool` — bars capped at **252** rows

**GetCompanyFinancialsFromYfInput**: exactly one of `index_id`, `isin`, `yahoo_symbol` + optional `include_statements: bool` (default `true`)

**GetCompanyFinancialsFromYfOutput**: `yahoo_symbol`, `index_type`, `info: dict` (subset of key `.info` fields), optional `income_statement`, `balance_sheet`, `cash_flow` as serializable records, `fetched_at`, `resolved_from_db: bool`

**GetAssetNewsFromYfInput**: exactly one identity field + optional `limit: int` (default 10, max 25)

**YahooNewsItem**: `title`, `link`, `publisher`, `published_at` (nullable)

**GetAssetNewsFromYfOutput**: `yahoo_symbol`, `items: list[YahooNewsItem]`, `count: int`, `resolved_from_db: bool`

**SearchYahooSymbolInput**: exactly one of `query: str | None`, `isin: str | None`, `index_id: UUID | None`

**SearchYahooSymbolOutput**: `yahoo_symbol`, `name`, `isin`, `index_id`, `index_type`, `exchange`, `quote_type`, `resolved_from_db: bool`

**UpdateIndexYahooSymbolInput**: `index_id: UUID`, `yahoo_symbol: str` (min 1, max 32)

**UpdateIndexYahooSymbolOutput**: `index_id`, `name`, `isin`, `index_type`, `yahoo_symbol`

Portfolio schemas (`PositionItem`, `IndexDetailOutput`, `IndexListItem`) MUST include `yahoo_symbol: str | None`.

`CreateIndexInput` MUST accept optional `yahoo_symbol: str | None` (max 32).

#### Scenario: Schema rejects multiple identity keys
- **WHEN** `GetAssetPriceFromYfInput` is built with both `isin` and `yahoo_symbol`
- **THEN** Pydantic validation fails before any yfinance call

### Requirement: GetAssetPriceFromYfTool
`GetAssetPriceFromYfTool` MUST resolve symbol via `YahooIndexResolver` (unless raw `yahoo_symbol` supplied) and return live spot data from yfinance.

MUST NOT fetch Bourso data in the same invocation.

#### Scenario: Price by index_id
- **WHEN** called with `index_id` for a COMPANY index with cached `yahoo_symbol="AI.PA"`
- **THEN** output includes non-null `last_price` when Yahoo returns a quote
- **AND** `resolved_from_db=true`

#### Scenario: Raw symbol without index row
- **WHEN** called with `yahoo_symbol="CW8.PA"` only
- **THEN** price is fetched without DB lookup
- **AND** no index row is created or updated

### Requirement: GetAssetHistoryFromYfTool
`GetAssetHistoryFromYfTool` MUST return OHLCV bars for the resolved symbol.

#### Scenario: One-year daily history
- **WHEN** called with `index_id` and `period="1y"`, `interval="1d"`
- **THEN** `bars` contains up to 252 daily entries ordered oldest-first
- **AND** each bar has `date`, `open`, `high`, `low`, `close`, `volume`

### Requirement: GetCompanyFinancialsFromYfTool
`GetCompanyFinancialsFromYfTool` MUST fetch structured financial data on demand.

MUST reject `index_type=ETF` when resolved from `index_id` or `isin`.

MUST NOT run on cron or market-session hooks — agent invocation only.

Does **not** replace Bourso key figures (`get_data_from_url` on `key_figures_url`).

#### Scenario: COMPANY financials returned
- **WHEN** called with `index_id` where `index_type=COMPANY` and symbol resolves
- **THEN** output includes `info` with at least `sector`, `marketCap`, `trailingPE` when Yahoo provides them
- **AND** optional statement tables are present when `include_statements=true`

#### Scenario: ETF rejected
- **WHEN** called with `index_id` where `index_type=ETF`
- **THEN** the tool raises an error before yfinance financials fetch
- **AND** message directs agent to use `get_etf_composition` and price/history tools instead

### Requirement: GetAssetNewsFromYfTool
`GetAssetNewsFromYfTool` MUST fetch live ticker news via yfinance `Search(symbol).news`.

MUST NOT merge or deduplicate with Bourso `news_items` cache in the same call.

Complements — does not replace — `get_financials_news_from_bourso` and `get_data_from_url`.

#### Scenario: Ticker news returned
- **WHEN** called with `yahoo_symbol="AI.PA"` and `limit=5`
- **THEN** `items` contains up to 5 headlines with `title` and `link`
- **AND** no SQL query to `news_items` occurs

### Requirement: SearchYahooSymbolTool
`SearchYahooSymbolTool` MUST perform DB-first resolution via `YahooIndexResolver` using yfinance **Lookup** (not Search).

#### Scenario: Search by ISIN
- **WHEN** called with `isin` for an index without cached symbol
- **AND** Lookup finds `AI.PA`
- **THEN** output includes `yahoo_symbol="AI.PA"` and auto-persisted DB value
- **AND** `resolved_from_db=false`

#### Scenario: No match
- **WHEN** Lookup returns zero hits
- **THEN** clear error for agent consumption

### Requirement: UpdateIndexYahooSymbolTool
`UpdateIndexYahooSymbolTool` MUST manually override `indices.yahoo_symbol`.

#### Scenario: Manual correction
- **WHEN** called with valid `index_id` and `yahoo_symbol="MC.PA"`
- **THEN** row is updated and output reflects change

### Requirement: No automatic dual-fetch with Bourso
Yahoo tools MUST NOT invoke Bourso HTTP clients. Bourso tools MUST NOT invoke yfinance. Agents choose source explicitly per workflow.

#### Scenario: Yahoo price tool isolation
- **WHEN** `get_asset_price_from_yf` runs
- **THEN** no `BoursoramaHttpClient` request is made

### Requirement: ToolRegistry exposes Yahoo market tools
`ToolRegistry.all_tools()` MUST include:

- `get_asset_price_from_yf`
- `get_asset_history_from_yf`
- `get_company_financials_from_yf`
- `get_asset_news_from_yf`
- `search_yahoo_symbol`
- `update_index_yahoo_symbol`

#### Scenario: Registry construction
- **WHEN** `ToolRegistry` is built at app bootstrap
- **THEN** all six Yahoo tools are present in `all_tools()`
- **AND** default `price_provider` is `YfinanceMarketPriceProvider`

### Requirement: Subagent Yahoo tool assignment

| Subagent | Yahoo tools |
|----------|-------------|
| Macro Strategist | `get_asset_price_from_yf`, `get_asset_history_from_yf`, `get_asset_news_from_yf` |
| Sector Analyst | Macro set + `get_company_financials_from_yf`, `search_yahoo_symbol`, `update_index_yahoo_symbol` |
| ETF Quant Specialist | Macro set (no `get_company_financials_from_yf`) |
| Portfolio Manager | none |

All subagents retain Bourso tools from prior change (with renamed news tool).

#### Scenario: Sector analyst has financials tool
- **WHEN** `SectorAnalystAgent.tools()` is called
- **THEN** the list includes `get_company_financials_from_yf` and `search_yahoo_symbol`

#### Scenario: ETF quant excludes company financials
- **WHEN** `EtfQuantSpecialistAgent.tools()` is called
- **THEN** the list includes `get_asset_price_from_yf` but NOT `get_company_financials_from_yf`

### Requirement: Enriched Yahoo tool docstrings
Every Yahoo `@tool` callable MUST have a multi-line docstring with sections: first-line summary, `Use when:`, `Do not use when:`, `Returns:`.

Docstrings MUST state:

- Yahoo data is delayed/unofficial
- `get_company_financials_from_yf` is COMPANY-only
- Bourso news cache is `get_financials_news_from_bourso`, not this tool

#### Scenario: Price tool docstring format
- **WHEN** `GetAssetPriceFromYfTool.as_tool()` is inspected
- **THEN** the bound tool's `description` contains `Use when:`, `Do not use when:`, and `Returns:` sections
