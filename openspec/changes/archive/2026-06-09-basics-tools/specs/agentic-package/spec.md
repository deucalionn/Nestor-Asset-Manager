## ADDED Requirements

### Requirement: ToolRegistry exposes all basics-tools
`ToolRegistry` MUST instantiate every basics-tool (eight tools) bound to a `NamRuntimeContext` (or runtime `user_id`) and expose them via `all_tools() -> list[BaseTool]`.

#### Scenario: Registry returns complete tool set
- **WHEN** `ToolRegistry(session_factory, context).all_tools()` is called
- **THEN** eight LangChain tools are returned with distinct snake_case names

#### Scenario: No agent assignment in registry
- **WHEN** `ToolRegistry` is reviewed
- **THEN** it does not implement PM vs sub-agent grouping — assignment is deferred to a follow-up change

### Requirement: Agent classes unchanged in this change
`PortfolioManagerAgent.tools()` and subagent `tools()` MAY remain empty stubs until a follow-up change assigns tools from the registry.

#### Scenario: Agents not wired yet
- **WHEN** this change is complete
- **THEN** agent `tools()` methods are not required to return registry tools
