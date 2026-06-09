## Requirements

### Requirement: GetFinancialsNewsFromBoursoTool
`GetFinancialsNewsFromBoursoTool` MUST query `news_items` and return newest-first results matching filters. It MUST NOT fetch external URLs.

Primary news source for **macro briefs** and **ETF context** (no per-ETF news page exists).

It MUST NOT be documented or prompted as the primary source for **Boursorama calendar tables**. Calendar context for agents comes from `/shared/calendar/today.md` on the Deep Agent backend (see `bourso-calendar-shared-file` spec).

`CALENDAR_*` category filters MAY remain valid for querying legacy cached rows but agents MUST prefer the shared calendar file for same-day macro scheduling.

#### Scenario: Filter by macro calendar legacy rows
- **WHEN** the tool is called with `category=CALENDAR_MACRO` and `since_hours=24`
- **THEN** only rows with that category and `fetched_at` within the window are returned
- **AND** results are ordered by `COALESCE(published_at, fetched_at)` descending

#### Scenario: ETF analyst uses global feeds
- **WHEN** ETF Quant calls with `category=MARKETS` or `category=FINANCE`
- **THEN** ingested global headlines are returned without per-ETF HTTP fetch

#### Scenario: Semantic news recall
- **WHEN** the tool is called with `semantic_query="inflation BCE"` and `since_hours=168`
- **THEN** rows with non-null `content_embedding` are ranked by cosine similarity
- **AND** results below `min_similarity` are excluded

### Requirement: Agent workflow source separation for calendars
Agent prompts MUST treat:

| Need | Source |
|------|--------|
| Same-day calendar (times, macro events, dividends) | `read_file("/shared/calendar/today.md")` |
| Market/finance headlines | `get_financials_news_from_bourso` with `MARKETS` or `FINANCE` |
| Company-specific news | `get_data_from_url` / company news index |

#### Scenario: Macro workflow prefers shared file at session start
- **WHEN** Macro Strategist prepares a session brief
- **THEN** prompts direct it to prefer `read_file` on `/shared/calendar/today.md` at session start
- **AND** optional `get_financials_news_from_bourso(MARKETS|FINANCE)` follows for headlines — not `CALENDAR_*` filters
