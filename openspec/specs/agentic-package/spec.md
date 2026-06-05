## ADDED Requirements

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

#### Scenario: Tool base class
- **WHEN** reviewing `nam_agentic/tools/base.py`
- **THEN** `BaseNamTool` is defined as an abstract base class

### Requirement: Deep agent factory stub
`DeepAgentFactory` MUST exist and expose a `build()` method that calls `create_deep_agent()` from the `deepagents` package.

#### Scenario: Factory builds graph
- **WHEN** `DeepAgentFactory(...).build()` is called with valid configuration
- **THEN** a compiled LangGraph agent is returned (may use stub tools in this change)

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
`nam_api/settings.py` and `nam_agentic/settings.py` MUST exist as pydantic-settings classes for package-specific configuration. Agentic settings include: `LLM_MODEL`, `LLM_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `DEFAULT_USER_ID`, `MARKET_TIMEZONE`.

#### Scenario: Settings modules exist
- **WHEN** each package is scaffolded
- **THEN** `nam_api/settings.py` and `nam_agentic/settings.py` load from `.env` without error

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
