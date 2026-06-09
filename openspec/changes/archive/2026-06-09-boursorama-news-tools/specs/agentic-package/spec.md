## MODIFIED Requirements

### Requirement: OOP tool classes
All custom tools MUST be classes inheriting from `BaseNamTool` with an `as_tool()` method returning a LangChain tool.

The `nam-agentic` tool set MUST include market tools (`GetFinancialsNewsTool`, `GetDataFromUrlTool`, `SearchBoursoramaTool`, `GetEtfCompositionTool`, `UpdateIndexBoursoramaTool`) in addition to basics-tools.

#### Scenario: Tool base class
- **WHEN** reviewing `nam_agentic/tools/base.py`
- **THEN** `BaseNamTool` is defined as an abstract base class

#### Scenario: Market tool classes exist
- **WHEN** reviewing `nam_agentic/tools/market/`
- **THEN** classes exist for all five market tools listed above
- **AND** each implements `as_tool()` returning a LangChain `BaseTool`

### Requirement: Subagent tool wiring for news workflows
Sector Analyst and ETF Quant Specialist subagents MUST expose portfolio read tools (`get_index`, `get_portfolio_positions`) in addition to analysis tools, so DB-first `boursorama_ticker` and `index_type` resolution works without PM delegation.

#### Scenario: Sector analyst portfolio read access
- **WHEN** `SectorAnalystAgent.tools()` is reviewed after this change
- **THEN** it includes `get_index` and `get_portfolio_positions`

### Requirement: Enriched tool docstrings
Every LangChain `@tool` callable (basics-tools **and** new market tools) MUST have a **multi-line** docstring exposed to the LLM. One-line docstrings are insufficient.

Each docstring MUST include these labeled sections:

| Section | Content |
|---------|---------|
| First line | Imperative one-line summary (becomes short description preview) |
| `Use when:` | Concrete situations to invoke the tool |
| `Do not use when:` | Anti-patterns, wrong `index_type`, or superseding tools |
| `Returns:` | Output shape in plain language (not raw Pydantic field names only) |

Market tools MUST document `COMPANY` vs `ETF` eligibility where relevant.

There is no `get_tools` meta-tool — docstrings are the runtime tool catalog for the model.

#### Scenario: Market tool docstring is multi-line
- **WHEN** `GetEtfCompositionTool.as_tool()` is inspected
- **THEN** the bound tool's `description` contains `Use when:`, `Do not use when:`, and `Returns:` sections

#### Scenario: Existing basics-tools docstrings upgraded
- **WHEN** any tool under `nam_agentic/tools/memory/` or `nam_agentic/tools/portfolio/` is reviewed after this change
- **THEN** its `@tool` docstring follows the enriched format (not a single sentence)
