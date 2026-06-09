## Requirements

### Requirement: GetFinancialsNewsFromBoursoTool
`GetFinancialsNewsFromBoursoTool` (formerly `GetFinancialsNewsTool` / LangChain name `get_financials_news`) MUST query `news_items` and return newest-first results matching filters. It MUST NOT fetch external URLs or yfinance.

Primary news source for **macro briefs** and **ETF context** (cron-refreshed Bourso MARKETS/FINANCE ingest).

Calendar tables are NOT the primary use case — see `agentic-news-tools` and `bourso-calendar-shared-file` specs.

#### Scenario: Filter by macro calendar legacy rows
- **WHEN** the tool is called with `category=CALENDAR_MACRO` and `since_hours=24`
- **THEN** only rows with that category and `fetched_at` within the window are returned
- **AND** results are ordered by `COALESCE(published_at, fetched_at)` descending

#### Scenario: Semantic news recall
- **WHEN** the tool is called with `semantic_query="inflation BCE"` and `since_hours=168`
- **THEN** rows with non-null `content_embedding` are ranked by cosine similarity
- **AND** results below `min_similarity` are excluded

### Requirement: ToolRegistry Bourso news tool name
`ToolRegistry.all_tools()` MUST register the Bourso news tool as `get_financials_news_from_bourso`.

The name `get_financials_news` MUST NOT appear in `ToolRegistry`, subagent `tools()` lists, or agent prompts after this change.

#### Scenario: Registry uses new name
- **WHEN** `ToolRegistry` is built at app bootstrap
- **THEN** `get_financials_news_from_bourso` is present
- **AND** `get_financials_news` is absent

### Requirement: Prompt and cross-tool references updated
All references in `nam_agentic/prompts/*.md` and tool docstrings that mention `get_financials_news` MUST be updated to `get_financials_news_from_bourso`.

Cross-references (e.g. `search_past_analyses` docstring) MUST point to the new name.

#### Scenario: Macro prompt references Bourso cache tool
- **WHEN** `MACRO_STRATEGIST.md` is reviewed
- **THEN** it documents `get_financials_news_from_bourso` for MARKETS/FINANCE headlines
- **AND** does not mention `get_financials_news`
- **AND** calendar context comes from `/shared/calendar/today.md` (not `CALENDAR_*` SQL filters)

### Requirement: Subagent Bourso news wiring
Subagents MUST expose the Bourso news tool as follows:

| Subagent | Bourso news tool |
|----------|------------------|
| Macro Strategist | `get_financials_news_from_bourso`, `get_data_from_url` |
| Sector Analyst | above + Bourso search/update tools |
| ETF Quant Specialist | above + `get_etf_composition` |

#### Scenario: Macro strategist tool list
- **WHEN** `MacroStrategistAgent.tools()` is called
- **THEN** the list includes `get_financials_news_from_bourso`
- **AND** does not include `get_financials_news`
