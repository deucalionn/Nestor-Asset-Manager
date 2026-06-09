## Requirements

### Requirement: ToolRegistry exposes all basics-tools
`ToolRegistry` MUST instantiate every basics-tool (eight tools) bound to a `NamRuntimeContext` (or runtime `user_id`) and expose them via `all_tools() -> list[BaseTool]`.

#### Scenario: Registry returns complete basics set
- **WHEN** `ToolRegistry(session_factory, context).all_tools()` is called
- **THEN** eight LangChain basics-tools are returned with distinct snake_case names

### Requirement: Enriched tool docstrings
Every LangChain `@tool` callable (basics-tools **and** market tools) MUST have a **multi-line** docstring exposed to the LLM. One-line docstrings are insufficient.

Each docstring MUST include these labeled sections:

| Section | Content |
|---------|---------|
| First line | Imperative one-line summary (becomes short description preview) |
| `Use when:` | Concrete situations to invoke the tool |
| `Do not use when:` | Anti-patterns, wrong `index_type`, or superseding tools |
| `Returns:` | Output shape in plain language (not raw Pydantic field names only) |

Market tools MUST document `COMPANY` vs `ETF` eligibility where relevant.

#### Scenario: Market tool docstring is multi-line
- **WHEN** `GetEtfCompositionTool.as_tool()` is inspected
- **THEN** the bound tool's `description` contains `Use when:`, `Do not use when:`, and `Returns:` sections

### Requirement: Agentic package layout
The `nam-agentic` package MUST follow the OOP directory structure defined in `openspec.md` section 2.1.

#### Scenario: Directory structure
- **WHEN** the package is scaffolded
- **THEN** the following modules exist: `factory.py`, `runner.py`, `context.py`, `enums.py`, `agents/`, `prompts/`, `tools/`, `scheduler/`

### Requirement: OOP agent classes
Agent definitions MUST be classes inheriting from `BaseSubAgent` (subagents) or `PortfolioManagerAgent` (main agent) — not raw dict configs.

#### Scenario: Subagent class exists
- **WHEN** `SectorAnalystAgent` is instantiated
- **THEN** it exposes `name`, `description`, `prompt_file`, `tools()`, and `to_spec()` methods

### Requirement: OOP tool classes
All custom tools MUST be classes inheriting from `BaseNamTool` with an `as_tool()` method returning a LangChain tool.

The `nam-agentic` tool set MUST include Bourso market tools (`GetFinancialsNewsFromBoursoTool`, `GetDataFromUrlTool`, `SearchBoursoramaTool`, `GetEtfCompositionTool`, `UpdateIndexBoursoramaTool`, `FetchCalendarFromBoursoTool`) and Yahoo market tools (`GetAssetPriceFromYfTool`, `GetAssetHistoryFromYfTool`, `GetCompanyFinancialsFromYfTool`, `GetAssetNewsFromYfTool`, `SearchYahooSymbolTool`, `UpdateIndexYahooSymbolTool`) in addition to basics-tools.

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

#### Scenario: Calendar fetch tool class exists
- **WHEN** reviewing `nam_agentic/tools/market/`
- **THEN** `FetchCalendarFromBoursoTool` exists
- **AND** LangChain-exposed name is `fetch_calendar_from_bourso`

### Requirement: Deep agent factory stub
`DeepAgentFactory` MUST exist and expose a `build()` method that calls `create_deep_agent()` from the `deepagents` package.

`build()` MUST pass `backend=build_agent_backend()` (see `agent-shared-backend` spec) so PM and subagents share `/shared/` on a volume-backed `FilesystemBackend`.

#### Scenario: Factory builds graph with shared backend
- **WHEN** `DeepAgentFactory(...).build()` is called with valid configuration
- **THEN** a compiled LangGraph agent is returned
- **AND** `create_deep_agent` receives a `CompositeBackend` with `/shared/` routed to `{agent_workspace_dir}/shared`

#### Scenario: Factory builds graph
- **WHEN** `DeepAgentFactory(...).build()` is called with valid configuration
- **THEN** a compiled LangGraph agent is returned (may use stub tools in this change)

### Requirement: Portfolio Manager calendar tool wiring
`PortfolioManagerAgent.tools()` MUST include `fetch_calendar_from_bourso` from `ToolRegistry`.

No subagent class MAY include `fetch_calendar_from_bourso`.

#### Scenario: Registry exposes calendar fetch on PM path only
- **WHEN** `ToolRegistry` is constructed
- **THEN** a `fetch_calendar_from_bourso` tool is available for PM wiring
- **AND** Sector, Macro, and ETF subagent tool lists exclude it

### Requirement: Agent runner
`AgentRunner` MUST wrap the compiled agent with `invoke()` and `stream()` async methods accepting `NamRuntimeContext`.

#### Scenario: Runner interface
- **WHEN** `AgentRunner` is reviewed
- **THEN** it exposes `async def invoke(message: str, context: NamRuntimeContext)` and `async def stream(...)`

### Requirement: Runtime enums
`nam_agentic/enums.py` MUST define `Market` and `MarketPhase` enums for scheduler and runtime context.

#### Scenario: Market phase enum values
- **WHEN** `MarketPhase.PRE_OPEN` is accessed
- **THEN** its value is `"PRE_OPEN"`

### Requirement: NamRuntimeContext
`nam_agentic/context.py` MUST define a frozen dataclass `NamRuntimeContext` with fields: `user_id`, `market`, `phase`, `thread_id`.

#### Scenario: Context creation
- **WHEN** `NamRuntimeContext(user_id=..., market=Market.EU, phase=MarketPhase.PRE_OPEN)` is constructed
- **THEN** the instance is immutable (`frozen=True`)

### Requirement: Package-specific settings
`nam_api/settings.py` and `nam_agentic/settings.py` MUST exist as pydantic-settings classes for package-specific configuration. Agentic settings include: `LLM_MODEL`, `LLM_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `DEFAULT_USER_ID`, `MARKET_TIMEZONE`, `AGENT_WORKSPACE_DIR`, `yahoo_resolve_prefer_suffix`, `yahoo_request_timeout_sec`.

#### Scenario: Settings modules exist
- **WHEN** each package is scaffolded
- **THEN** `nam_api/settings.py` and `nam_agentic/settings.py` load from `.env` without error
- **AND** Yahoo settings have documented defaults

### Requirement: Markdown prompt files
System prompts MUST live as markdown files in `nam_agentic/prompts/`: `PORTFOLIO.md`, `SECTOR_ANALYST.md`, `MACRO_STRATEGIST.md`, `ETF_QUANT.md`. A `PromptLoader` class reads `{NAME}.md` by filename (without extension).

#### Scenario: Prompt file coverage
- **WHEN** reviewing `nam_agentic/prompts/`
- **THEN** one `.md` file exists per agent (PM + 3 subagents)
- **AND** no Python prompt class modules exist

### Requirement: Scheduler skeleton
`nam_agentic/scheduler/` MUST contain `markets.py` (market session definitions) and `worker.py` (APScheduler entry point stub).

#### Scenario: Worker module runnable
- **WHEN** `python -m nam_agentic.scheduler.worker` is executed
- **THEN** the module loads and prints a startup message without crashing

### Requirement: Package dependency on nam-db
`nam-agentic` MUST depend on `nam-db` via uv path dependency. It MUST NOT depend on `nam-api`.

#### Scenario: Dependency direction
- **WHEN** `uv tree` is run for `agentic/`
- **THEN** `nam-db` is listed as a dependency and `nam-api` is absent

### Requirement: No hand-built LangGraph graphs
The agentic package MUST NOT contain manual `StateGraph` node/edge wiring. Orchestration MUST go through `create_deep_agent()`.

#### Scenario: No StateGraph usage
- **WHEN** searching `agentic/` for `StateGraph` imports
- **THEN** none are found outside of comments or documentation

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
