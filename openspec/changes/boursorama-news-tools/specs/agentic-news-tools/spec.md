## ADDED Requirements

### Requirement: Market news Pydantic schemas
`nam_agentic/tools/schemas/market.py` MUST define:

**GetFinancialsNewsInput**

| Field | Type | Constraints |
|-------|------|-------------|
| `category` | NewsCategory \| None | optional filter |
| `keyword` | str \| None | optional ILIKE on title+summary |
| `semantic_query` | str \| None | optional pgvector similarity search |
| `since_hours` | int \| None | default 48, min 1, max 168 |
| `boursorama_ticker` | str \| None | optional |
| `limit` | int | default 20, min 1, max 50 |
| `min_similarity` | float | default 0.7, min 0, max 1 — used with `semantic_query` |

**NewsItemOutput** (list element): `id`, `source`, `category`, `title`, `source_url`, `summary`, `boursorama_ticker`, `published_at`, `fetched_at`, optional `similarity_score`

**GetFinancialsNewsOutput**: `items: list[NewsItemOutput]`, `count: int`

**GetDataFromUrlInput**: `url: str` (max 2048), `persist: bool` (default `true` for article deep-reads)

**CompanyNewsHeadline**: `title`, `summary`, `article_url`, `published_at`, `attribution` (all str except dates; `attribution` nullable)

**GetDataFromUrlOutput** — discriminated by `content_type`:

| Field | `news_index` | `article` |
|-------|--------------|-----------|
| `url` | required | required |
| `title` | page title | article title |
| `content_type` | `news_index` | `article` |
| `headlines` | `list[CompanyNewsHeadline]`, min 1 | null |
| `markdown` | null | LLM-formatted body |
| `fetched_at` | required | required |
| `persisted` | false | true when article upserted to `news_items` |
| `news_item_id` | null | UUID when persisted |

**SearchBoursoramaInput**: `query: str | None`, `isin: str | None`, `index_id: UUID | None` — validator: exactly one required

**SearchBoursoramaOutput**: `boursorama_ticker`, `name`, `isin`, `index_id`, `index_type`, `quote_url`, `news_url`, `key_figures_url`, `composition_url`, `resolved_from_db: bool`

- When `index_type=COMPANY`: `news_url` and `key_figures_url` populated; `composition_url=null`
- When `index_type=ETF`: `composition_url` populated; `news_url=null`, `key_figures_url=null`

**GetEtfCompositionInput**: `index_id: UUID | None`, `boursorama_ticker: str | None` — validator: exactly one required

**EtfHoldingItem**: `name: str`, `weight_pct: float | None`, `isin: str | None`, `boursorama_ticker: str | None`

**GetEtfCompositionOutput**: `index_id`, `boursorama_ticker`, `composition_url`, `holdings: list[EtfHoldingItem]`, `fetched_at`

**UpdateIndexBoursoramaInput**: `index_id: UUID`, `boursorama_ticker: str` (min 1, max 32)

**UpdateIndexBoursoramaOutput**: `index_id`, `name`, `isin`, `index_type`, `boursorama_ticker`

`IndexDetailOutput`, `IndexListItem`, and `PositionItem` MUST include `index_type: IndexType` and `boursorama_ticker: str | None`.

`CreateIndexInput` MUST accept `index_type: IndexType` (required) and optional `boursorama_ticker: str | None` (max 32).

#### Scenario: Schema validation rejects multiple search keys
- **WHEN** `SearchBoursoramaInput` is built with more than one of `query`, `isin`, `index_id`
- **THEN** Pydantic validation fails before any HTTP request

### Requirement: GetFinancialsNewsTool
`GetFinancialsNewsTool` MUST query `news_items` and return newest-first results matching filters. It MUST NOT fetch external URLs.

Primary news source for **macro briefs** and **ETF context** (no per-ETF news page exists).

#### Scenario: Filter by macro calendar
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

### Requirement: Agent article persist
`GetDataFromUrlTool` MUST upsert `news_items` when `persist=true` and `content_type=article`.

Each persisted article MUST set `content_markdown`, compute `content_embedding`, and upsert by `source_url`.

`news_index` responses MUST NOT persist rows.

#### Scenario: Article deep-read persisted
- **WHEN** agent calls `get_data_from_url` on an article URL with default `persist`
- **THEN** `content_type=article`, `persisted=true`, and a `news_items` row exists with `content_markdown`
- **AND** a subsequent call with the same URL updates the row without creating a duplicate

#### Scenario: Re-fetch preserves enriched body on cron refresh
- **WHEN** cron ingest upserts a headline whose `source_url` already has `content_markdown` from agent persist
- **THEN** `content_markdown` is unchanged
- **AND** `content_embedding` is recomputed from title, summary, and existing markdown

### Requirement: Company news index parser
`company_news_parser.py` MUST parse `/cours/actualites/{ticker}/` pages into `CompanyNewsHeadline` items.

**Only for `index_type=COMPANY`.** MUST NOT be invoked for ETF tickers.

#### Scenario: Company news index returns all visible headlines
- **WHEN** `get_data_from_url` is called with `url=https://www.boursorama.com/cours/actualites/1rPAI/`
- **THEN** `content_type` is `news_index`
- **AND** `headlines` contains at least one item with `title`, `summary`, and `article_url`
- **AND** `markdown` is null

### Requirement: Global actualites hub
`get_data_from_url` MUST support `https://www.boursorama.com/bourse/actualites/` (and `bourse.boursobank.com` equivalent) using `list_parser` to return `content_type=news_index` with headlines + teasers + article links.

Useful for ETF analysis when combined with `get_financials_news` and composition holdings.

#### Scenario: Global hub returns headlines
- **WHEN** `get_data_from_url` is called with the global actualites hub URL
- **THEN** `content_type` is `news_index`
- **AND** `headlines` is non-empty when the page contains entries

### Requirement: PageContentFormatter pipeline
`PageContentFormatter` applies to full-page deep reads (article URLs, key figures, generic editorial) — **not** news index listings or ETF composition.

Sequence: `httpx` → `trafilatura` → LLM. Input is trafilatura output truncated to `news_format_max_chars`. `page_hint`: `article`, `company_key_figures`, `generic`.

When `news_format_llm_enabled=false`, return trafilatura output without LLM.

#### Scenario: Empty extraction
- **WHEN** trafilatura returns empty or whitespace-only text
- **THEN** the formatter raises an error before any LLM call

### Requirement: GetDataFromUrlTool uses shared HTTP client
`GetDataFromUrlTool` MUST fetch via `BoursoramaHttpClient` only. At most one HTTP GET per invocation.

Allowed hosts: `www.boursorama.com`, `bourse.boursobank.com`. Allowed path prefixes: `/bourse/`, `/cours/`.

#### Scenario: ETF company-news URL rejected
- **WHEN** the tool is called with a company news URL (`/cours/actualites/`) for an index known to be `index_type=ETF`
- **THEN** the tool raises an error explaining ETFs have no company news page
- **AND** suggests `get_etf_composition` + global news instead

### Requirement: GetDataFromUrlTool routing
`page_reader.py` routes:

- `/cours/actualites/{ticker}/` → `company_news_parser` (COMPANY only)
- `/bourse/actualites/` → global hub `list_parser`
- Article URL → `PageContentFormatter`
- `/cours/societe/chiffres-cles/{ticker}/` → `PageContentFormatter` (COMPANY only)

#### Scenario: Agent deep-reads article after index scan
- **WHEN** agent calls `get_data_from_url` on company news index then on one `article_url`
- **THEN** first response is `news_index`, second is `article` with `markdown`

#### Scenario: Company key figures
- **WHEN** called with `https://www.boursorama.com/cours/societe/chiffres-cles/1rPAI/`
- **THEN** `content_type=article` with non-empty `markdown` and `page_hint=company_key_figures`

#### Scenario: SSRF blocked
- **WHEN** called with `url=https://evil.example.com/`
- **THEN** error before any outbound request

### Requirement: GetEtfCompositionTool
`GetEtfCompositionTool` MUST fetch and parse the tracker composition page.

Target URL: `https://bourse.boursobank.com/bourse/trackers/cours/composition/{ticker}/`

MUST require `indices.index_type=ETF` when `index_id` is provided. MUST reject `index_type=COMPANY`.

Parser (`etf_composition_parser.py`) extracts holdings: `name`, optional `weight_pct`, optional `isin`, optional `boursorama_ticker` per line when present in HTML.

Single HTTP request per invocation. No LLM on composition parse.

#### Scenario: ETF composition parsed
- **WHEN** called with `index_id` for an ETF with `boursorama_ticker="1rTPUST"`
- **THEN** `holdings` contains at least one `EtfHoldingItem` with non-empty `name`
- **AND** `composition_url` matches the BoursoBank composition pattern

#### Scenario: COMPANY index rejected
- **WHEN** called with `index_id` where `index_type=COMPANY`
- **THEN** the tool raises an error before HTTP fetch

### Requirement: BoursoramaIndexResolver DB-first lookup
Resolution order:

1. Load `indices` by `index_id` or `isin`; if `boursorama_ticker` set → return type-aware URLs, `resolved_from_db=true`
2. On cache miss → HTTP search → auto-persist `boursorama_ticker` on matching row
3. Build URLs from `index_type` (see `SearchBoursoramaOutput`)

`UpdateIndexBoursoramaTool` is for **manual override only** — not the nominal persist path.

#### Scenario: Cache hit by index_id
- **WHEN** `SearchBoursoramaTool` is called with `index_id` and ticker already in DB
- **THEN** `resolved_from_db=true` and no HTTP request

#### Scenario: ETF returns composition URL not news URL
- **WHEN** resolved index has `index_type=ETF` and `boursorama_ticker="1rTPUST"`
- **THEN** `composition_url` is populated and `news_url` is null

### Requirement: SearchBoursoramaTool
DB-first resolution via `BoursoramaIndexResolver`. Type-aware canonical URLs per `index_type`.

#### Scenario: Search COMPANY by name
- **WHEN** called with `query="Air Liquide"` and resolved type is `COMPANY`
- **THEN** `news_url` and `key_figures_url` are populated

#### Scenario: No match
- **WHEN** search returns zero hits
- **THEN** clear error for agent consumption

### Requirement: UpdateIndexBoursoramaTool
Manual override of `indices.boursorama_ticker`. Nominal path is auto-persist via resolver.

#### Scenario: Manual correction
- **WHEN** called with valid `index_id` and new ticker
- **THEN** row is updated and output reflects change

### Requirement: ToolRegistry exposes market tools
`ToolRegistry.all_tools()` MUST include: `get_financials_news`, `get_data_from_url`, `search_boursorama`, `get_etf_composition`, `update_index_boursorama`.

#### Scenario: Registry construction
- **WHEN** `ToolRegistry` is built at app bootstrap
- **THEN** all five market tools are present in `all_tools()`

### Requirement: Subagent tool assignment

| Subagent | Tools |
|----------|-------|
| Macro Strategist | `get_financials_news`, `get_data_from_url` |
| Sector Analyst | Macro set + `search_boursorama`, `update_index_boursorama`, `get_index`, `get_portfolio_positions` |
| ETF Quant Specialist | Sector set + `get_etf_composition` |
| Portfolio Manager | no URL/search/ETF tools |

#### Scenario: Sector analyst can read index from DB
- **WHEN** `SectorAnalystAgent.tools()` is called
- **THEN** the list includes `get_index` and `get_portfolio_positions`

#### Scenario: ETF quant has composition tool
- **WHEN** `EtfQuantSpecialistAgent.tools()` is called
- **THEN** the list includes `get_etf_composition`
