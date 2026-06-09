## Requirements

### Requirement: Tool base class contract
Every agent tool MUST be a class inheriting from `BaseNamTool` in `nam_agentic/tools/base.py` and implement `as_tool() -> BaseTool` returning a LangChain-decorated async callable with a stable snake_case name.

#### Scenario: Tool instantiation
- **WHEN** a tool class is constructed with `async_sessionmaker`, runtime `user_id`, and required services
- **THEN** `as_tool()` returns a `BaseTool` callable by agents

### Requirement: Runtime user context injection
Tools MUST receive `user_id` from `NamRuntimeContext` at construction/bind time. Pydantic input schemas exposed to the LLM MUST NOT include `user_id`.

#### Scenario: LangChain args exclude user_id
- **WHEN** an agent invokes `create_analysis` via LangChain
- **THEN** the tool argument schema has no `user_id` field
- **AND** the persisted row uses the runtime context user

#### Scenario: Tests supply user explicitly
- **WHEN** a tool unit test constructs a tool with a fixture user UUID
- **THEN** database operations scope to that user without passing UUID in tool args

### Requirement: Typed tool schemas
Each tool MUST define Pydantic v2 input and output models under `nam_agentic/tools/schemas/`. Domain enums MUST be imported from `nam_db.enums` — not `Literal[...]`.

#### Scenario: Schema validation
- **WHEN** invalid ISIN or empty `analysis_ids` is passed to a tool input
- **THEN** Pydantic validation fails before any database access

### Requirement: CreateAnalysisTool
`CreateAnalysisTool` MUST persist an `analyses` row with embedding.

LLM-visible input (`CreateAnalysisInput`):

| Field | Type | Constraints |
|-------|------|-------------|
| `agent` | SubAgentRole | required — PM MUST NOT be accepted |
| `title` | str | min 1, max 255 |
| `content` | str | min 100 |
| `trigger` | AnalysisTrigger | required |
| `index_id` | UUID | optional |

Output (`CreateAnalysisOutput`): `analysis_id`, `agent` (AgentRole), `embedding_dimensions` (int, MUST be 384), `created_at`.

Embedding MUST use canonical text `f"{title}\n\n{content}"` before INSERT.

#### Scenario: Sub-agent creates analysis
- **WHEN** `CreateAnalysisTool` is invoked with `agent=SubAgentRole.SECTOR_ANALYST` and valid fields
- **THEN** a row exists in `analyses` for the runtime user with non-null embedding
- **AND** output `embedding_dimensions` equals 384

#### Scenario: PM role rejected
- **WHEN** input uses a role outside `SubAgentRole`
- **THEN** validation fails before persistence

### Requirement: CreateRecommendationTool
`CreateRecommendationTool` MUST create a `PENDING` recommendation linked to one or more analyses via `recommendation_analyses`.

LLM-visible input (`CreateRecommendationInput`):

| Field | Type | Constraints |
|-------|------|-------------|
| `analysis_ids` | list[UUID] | min length 1 |
| `content` | str | min 50 |
| `type` | RecommendationType | required |

Output (`CreateRecommendationOutput`): `recommendation_id`, `status` (always `PENDING`), `created_at`.

#### Scenario: Recommendation with multiple analyses
- **WHEN** the tool is called with three valid `analysis_ids` for the runtime user
- **THEN** one `recommendations` row is inserted with `status=PENDING` and `agent=PORTFOLIO_MANAGER`
- **AND** three rows exist in `recommendation_analyses`

#### Scenario: Unknown analysis rejected
- **WHEN** an `analysis_id` does not exist or belongs to another user
- **THEN** the tool raises an error and rolls back without inserting a recommendation

### Requirement: SearchPastAnalysesTool
`SearchPastAnalysesTool` MUST perform user-scoped semantic search over `analyses.content_embedding` using pgvector cosine distance.

LLM-visible input (`SearchPastAnalysesInput`):

| Field | Type | Default |
|-------|------|---------|
| `query` | str | min 10 |
| `top_k` | int | 5, range 1–20 |
| `agent_filter` | AgentRole \| None | None |
| `min_similarity` | float | 0.7, range 0.0–1.0 |

Output: list of `AnalysisSearchResult` with `analysis_id`, `agent`, `title`, `content_snippet`, `similarity_score`, `created_at`.

#### Scenario: RAG query returns ranked results
- **WHEN** similar analyses exist for the runtime user above `min_similarity`
- **THEN** results are ordered by descending similarity
- **AND** each result includes a non-empty `content_snippet`

#### Scenario: User isolation
- **WHEN** another user's analyses match the query vector
- **THEN** they are excluded from results

### Requirement: GetUserContextTool
`GetUserContextTool` MUST return the configured user's profile for personalization (strategy, goals).

LLM-visible input: none (empty model or unit struct).

Output (`UserContextOutput`): `user_id`, `firstname`, `date_of_birth`, `age` (computed at read time), `strategy`, `goals`.

#### Scenario: Profile loaded
- **WHEN** the tool is invoked for an initialized user
- **THEN** output includes `strategy` and `goals` from the `users` row

#### Scenario: Unknown user
- **WHEN** runtime `user_id` has no profile row
- **THEN** the tool raises a not-found error

### Requirement: GetPortfolioPositionsTool
`GetPortfolioPositionsTool` MUST return all positions for the runtime user joined with index metadata and optional gain/loss metrics.

LLM-visible input: none.

Output (`GetPortfolioPositionsOutput`):

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | UUID | runtime user |
| `positions` | list[PositionItem] | |
| `total_market_value` | Decimal \| None | sum when prices available |

Each `PositionItem` MUST include: `index_id`, `index_name`, `isin`, `quantity`, `average_cost`, `last_update`, `current_price` (optional), `market_value` (optional), `unrealized_pnl` (optional), **`gain_loss_pct: float | None`** — percentage vs average cost (e.g. `12.5` = +12.5%).

When `current_price` is unavailable, `gain_loss_pct` MUST be `null`.

#### Scenario: Position with price shows gain/loss percent
- **WHEN** a position has `average_cost=100` and the price provider returns `110`
- **THEN** `gain_loss_pct` is approximately `10.0` (float)

#### Scenario: Empty portfolio
- **WHEN** the user has no positions
- **THEN** `positions` is an empty list

### Requirement: CreateIndexTool
`CreateIndexTool` MUST create or return an existing index by ISIN (UPSERT semantics).

Input: `name` (1–255 chars), `isin` (12 chars, ISIN pattern).

Output: `index_id`, `name`, `isin`, `created` (bool — `false` if ISIN already existed).

#### Scenario: New ISIN
- **WHEN** ISIN is not in `indices`
- **THEN** a row is inserted and `created=true`

#### Scenario: Existing ISIN
- **WHEN** ISIN already exists
- **THEN** existing row is returned with `created=false` and no duplicate insert

### Requirement: GetIndexTool
`GetIndexTool` MUST fetch a single index by `index_id` or `isin` (exactly one identifier required).

Output: `index_id`, `name`, `isin`, `created_at`.

#### Scenario: Lookup by ISIN
- **WHEN** `isin` matches a catalog row
- **THEN** the index metadata is returned

#### Scenario: Not found
- **WHEN** neither identifier matches
- **THEN** the tool raises a not-found error

### Requirement: ListIndicesTool
`ListIndicesTool` MUST list indices from the catalog, optionally filtered by name substring.

LLM-visible input (`ListIndicesInput`):

| Field | Type | Default |
|-------|------|---------|
| `name_query` | str \| None | None — case-insensitive substring match on `indices.name` |

Output: `list[IndexListItem]` with `index_id`, `name`, `isin`, `created_at`, ordered by `name` ascending.

#### Scenario: Unfiltered list
- **WHEN** `name_query` is omitted
- **THEN** all indices are returned ordered by name

#### Scenario: Name search
- **WHEN** `name_query="google"` is passed and an index named `"Alphabet Inc (Google)"` exists
- **THEN** that index appears in results
- **AND** indices whose names do not contain the substring are excluded

### Requirement: Embedding service
Agentic MUST provide an `EmbeddingService` using `settings.embedding_model` and `settings.embedding_dim` (384). `CreateAnalysisTool` and `SearchPastAnalysesTool` MUST use this service.

#### Scenario: Dimension guard
- **WHEN** the embedding API returns a vector whose length is not 384
- **THEN** the service raises an error before database write

### Requirement: Market price provider
`GetPortfolioPositionsTool` MUST depend on a `MarketPriceProvider` protocol. Production defaults to `YfinanceMarketPriceProvider`; tests MUST use a fake or stub provider.

#### Scenario: Fake provider in tests
- **WHEN** tests configure ISIN → price mappings
- **THEN** `gain_loss_pct` is computed correctly

### Requirement: Agent write boundary
Tools in this change MUST NOT INSERT or UPDATE `transactions` or `positions`. Portfolio tools are read-only except index catalog writes.

#### Scenario: No ledger mutation
- **WHEN** any basics-tool executes
- **THEN** no rows are written to `transactions` or `positions`

### Requirement: Agentic tool tests
`agentic/tests/` MUST include tests for each tool covering happy path and primary error cases. Tests MUST run in CI via the project test harness (Docker Postgres).

#### Scenario: CI green
- **WHEN** `just test` runs
- **THEN** agentic basics-tool tests pass with embedding service mocked
