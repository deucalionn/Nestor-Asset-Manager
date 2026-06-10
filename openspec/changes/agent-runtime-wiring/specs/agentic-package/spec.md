## MODIFIED Requirements

### Requirement: Deep agent factory stub
`DeepAgentFactory` MUST exist and expose a `build()` method that calls `create_deep_agent()` from the `deepagents` package.

`build()` MUST pass:

- `backend=build_agent_backend()` (see `agent-shared-backend` spec)
- `checkpointer=` from application lifespan (see `agent-checkpointer` spec)

The built-in Deep Agents `general-purpose` subagent MUST be disabled via harness profile (`general_purpose_subagent.enabled=False`) so the PM delegates only to NAM-defined subagents (`macro-strategist`, `sector-analyst`, `etf-quant`).

#### Scenario: Factory builds graph with shared backend and checkpointer
- **WHEN** `DeepAgentFactory(...).build()` is called with valid configuration
- **THEN** a compiled LangGraph agent is returned
- **AND** `create_deep_agent` receives a `CompositeBackend` with `/shared/` and `/user/` routes
- **AND** a PostgreSQL checkpointer is attached

#### Scenario: General-purpose subagent disabled
- **WHEN** the compiled agent's available subagent types are inspected
- **THEN** `general-purpose` is not available for `task()` delegation
- **AND** `macro-strategist`, `sector-analyst`, and `etf-quant` remain available

## ADDED Requirements

### Requirement: Process-lifetime compiled graph
`nam-agentic` is a normal FastAPI service with **one warm agent** behind it. When the server process starts, the agent (PM + subagent specs + tools + backend + checkpointer) MUST be compiled **during lifespan startup** — before the app accepts traffic and before APScheduler fires the first job.

After startup, the process stays **idle** (no LLM calls) until triggered by an event (`POST /events`, cron) or chat (`POST /chat/stream`).

The same `AgentRunner` instance (holding the compiled graph) MUST serve all events and chat streams until the process exits.

`create_deep_agent()` MUST NOT be called per HTTP request, per event, or lazily on first use.

`EventHandler` MUST receive the lifespan-built `AgentRunner` by injection — not via a factory that builds the graph on first `_resolve_runner()` call.

#### Scenario: Agent ready before scheduler and requests
- **WHEN** `nam-agentic` lifespan enters
- **THEN** checkpointer setup and `DeepAgentFactory.build()` complete successfully
- **AND** `AgentRunner` is stored on application state
- **AND** only then does APScheduler start
- **AND** the lifespan context yields (server ready)

#### Scenario: Graph built at startup
- **WHEN** `nam-agentic` lifespan enters
- **THEN** `DeepAgentFactory.build()` runs once
- **AND** the resulting compiled graph is stored for reuse

#### Scenario: Invoke reuses live graph
- **WHEN** `market.session` and a subsequent `/chat/stream` request occur in the same process
- **THEN** both call `invoke()` or `stream()` on the same compiled graph instance
- **AND** no second `create_deep_agent()` call occurs between them

#### Scenario: v1 ToolRegistry at startup
- **WHEN** the agent graph is built at startup
- **THEN** `ToolRegistry` is constructed once with `settings.default_user_id`
- **AND** tools remain bound for the process lifetime (v1 single-user)

### Requirement: Sync subagents with parallel delegation
Subagents MUST remain **synchronous** (`task()` tool only — no async subagents in this change).

Within a single PM model turn, the harness MAY run multiple `task()` calls to NAM subagents **in parallel**; the PM MUST block until all delegated tasks return before continuing the committee review.

#### Scenario: Parallel task calls in one turn
- **WHEN** the PM invokes `task(macro-strategist)` and `task(sector-analyst)` in the same turn
- **THEN** both subagents may execute concurrently
- **AND** the PM receives both results before the next orchestration step

### Requirement: AgentRunner thread configuration
`AgentRunner.invoke()` and `AgentRunner.stream()` MUST pass LangGraph `config={"configurable": {"thread_id": ...}}` when `NamRuntimeContext.thread_id` is set.

For `market.session`, the runner MUST supply `thread_id` formatted as `market:{market}:{phase}:{date}` (ISO date, e.g. `market:EU:PRE_OPEN:2026-06-09`).

#### Scenario: Chat stream sets thread_id
- **WHEN** `AgentRunner.stream()` is called with `context.thread_id="abc"`
- **THEN** the LangGraph config includes `configurable.thread_id="abc"`

#### Scenario: Market session thread id is deterministic
- **WHEN** `market.session` invokes with `market=EU`, `phase=PRE_OPEN`, date `2026-06-09`
- **THEN** `configurable.thread_id` is `market:EU:PRE_OPEN:2026-06-09`
- **AND** chat threads using UUID `thread_id` values do not collide
