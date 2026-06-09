## MODIFIED Requirements

### Requirement: OOP tool classes
All custom tools MUST be classes inheriting from `BaseNamTool` with an `as_tool()` method returning a LangChain tool.

The `nam-agentic` tool set MUST include Bourso market tools (`GetFinancialsNewsFromBoursoTool`, `GetDataFromUrlTool`, `SearchBoursoramaTool`, `GetEtfCompositionTool`, `UpdateIndexBoursoramaTool`) and Yahoo market tools (`GetAssetPriceFromYfTool`, `GetAssetHistoryFromYfTool`, `GetCompanyFinancialsFromYfTool`, `GetAssetNewsFromYfTool`, `SearchYahooSymbolTool`, `UpdateIndexYahooSymbolTool`) in addition to basics-tools.

#### Scenario: Tool base class
- **WHEN** reviewing `nam_agentic/tools/base.py`
- **THEN** `BaseNamTool` is defined as an abstract base class

#### Scenario: Yahoo market tool classes exist
- **WHEN** reviewing `nam_agentic/tools/market/` and `nam_agentic/tools/services/yahoo/`
- **THEN** classes exist for all six Yahoo tools listed above
- **AND** each implements `as_tool()` returning a LangChain `BaseTool`

#### Scenario: Bourso news tool renamed class
- **WHEN** reviewing `nam_agentic/tools/market/`
- **THEN** `GetFinancialsNewsFromBoursoTool` exists (file may be `get_financials_news_from_bourso.py`)
- **AND** LangChain-exposed name is `get_financials_news_from_bourso`

### Requirement: Package-specific settings
`nam_api/settings.py` and `nam_agentic/settings.py` MUST exist as pydantic-settings classes for package-specific configuration. Agentic settings include: `LLM_MODEL`, `LLM_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `DEFAULT_USER_ID`, `MARKET_TIMEZONE`, `yahoo_resolve_prefer_suffix`, `yahoo_request_timeout_sec`.

#### Scenario: Settings modules exist
- **WHEN** each package is scaffolded
- **THEN** `nam_api/settings.py` and `nam_agentic/settings.py` load from `.env` without error
- **AND** Yahoo settings have documented defaults

## ADDED Requirements

### Requirement: Yahoo services package layout
`nam_agentic/tools/services/yahoo/` MUST contain:

| Module | Responsibility |
|--------|----------------|
| `client.py` | Async yfinance wrapper |
| `resolver.py` | `YahooIndexResolver` |
| `lookup.py` | Lookup filtering and `.PA` preference |
| `errors.py` | Typed Yahoo errors |

#### Scenario: Package importable
- **WHEN** `from nam_agentic.tools.services.yahoo.resolver import YahooIndexResolver` is executed
- **THEN** import succeeds without circular dependency on `nam-api`

### Requirement: Default price provider is yfinance
`ToolRegistry` MUST default to `YfinanceMarketPriceProvider` when no `price_provider` is injected.

`StubMarketPriceProvider` MUST remain available for tests that explicitly opt in.

#### Scenario: Production registry wiring
- **WHEN** `ToolRegistry(session_factory, user_id)` is constructed without `price_provider`
- **THEN** `get_portfolio_positions` uses `YfinanceMarketPriceProvider`

### Requirement: Subagent tool wiring for Yahoo workflows
Macro Strategist, Sector Analyst, and ETF Quant Specialist MUST expose Yahoo price/history/news tools per `agentic-yahoo-tools` spec. Sector Analyst MUST additionally expose financials and Yahoo symbol tools.

Portfolio read tools (`get_index`, `get_portfolio_positions`) MUST remain on Sector and ETF subagents for DB-first resolution.

#### Scenario: Macro strategist Yahoo access
- **WHEN** `MacroStrategistAgent.tools()` is reviewed after this change
- **THEN** it includes `get_asset_price_from_yf`, `get_asset_history_from_yf`, and `get_asset_news_from_yf`
