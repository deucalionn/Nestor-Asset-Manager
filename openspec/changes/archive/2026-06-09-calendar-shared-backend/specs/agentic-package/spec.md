## MODIFIED Requirements

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

### Requirement: OOP tool classes
All custom tools MUST be classes inheriting from `BaseNamTool` with an `as_tool()` method returning a LangChain tool.

The `nam-agentic` tool set MUST include Bourso market tools (`GetFinancialsNewsFromBoursoTool`, `GetDataFromUrlTool`, `SearchBoursoramaTool`, `GetEtfCompositionTool`, `UpdateIndexBoursoramaTool`, `FetchCalendarFromBoursoTool`) and Yahoo market tools (`GetAssetPriceFromYfTool`, `GetAssetHistoryFromYfTool`, `GetCompanyFinancialsFromYfTool`, `GetAssetNewsFromYfTool`, `SearchYahooSymbolTool`, `UpdateIndexYahooSymbolTool`) in addition to basics-tools.

#### Scenario: Tool base class
- **WHEN** reviewing `nam_agentic/tools/base.py`
- **THEN** `BaseNamTool` is defined as an abstract base class

#### Scenario: Calendar fetch tool class exists
- **WHEN** reviewing `nam_agentic/tools/market/`
- **THEN** `FetchCalendarFromBoursoTool` exists
- **AND** LangChain-exposed name is `fetch_calendar_from_bourso`

#### Scenario: Yahoo market tool classes exist
- **WHEN** reviewing `nam_agentic/tools/market/` and `nam_agentic/tools/services/yahoo/`
- **THEN** classes exist for all six Yahoo tools listed above
- **AND** each implements `as_tool()` returning a LangChain `BaseTool`

#### Scenario: Bourso news tool renamed class
- **WHEN** reviewing `nam_agentic/tools/market/`
- **THEN** `GetFinancialsNewsFromBoursoTool` exists (file may be `get_financials_news_from_bourso.py`)
- **AND** LangChain-exposed name is `get_financials_news_from_bourso`

## ADDED Requirements

### Requirement: Portfolio Manager calendar tool wiring
`PortfolioManagerAgent.tools()` MUST include `fetch_calendar_from_bourso` from `ToolRegistry`.

No subagent class MAY include `fetch_calendar_from_bourso`.

#### Scenario: Registry exposes calendar fetch on PM path only
- **WHEN** `ToolRegistry` is constructed
- **THEN** a `fetch_calendar_from_bourso` tool is available for PM wiring
- **AND** Sector, Macro, and ETF subagent tool lists exclude it
