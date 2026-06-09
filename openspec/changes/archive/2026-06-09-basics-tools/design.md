# Design — basics-tools

## Context

- **Done**: `nam_db` models, API read/feedback endpoints, `BaseNamTool`, stub `ToolRegistry`, agent classes with empty `tools()`.
- **This change**: implement tools + registry only. **Agent tool assignment** deferred to a follow-up change.
- **Constraints** (from `openspec.md`):
  - Agentic writes `analyses` / `recommendations` / junction rows — never `transactions` or `positions`
  - Recommendations always created as `PENDING`
  - Embeddings: `nomic-embed-text`, dimension **384**
  - No import of `nam-api` from agentic

## Goals / Non-Goals

**Goals:**

- Eight typed tools with Pydantic v2 schemas and `BaseNamTool.as_tool()`
- Runtime-scoped `user_id` from `NamRuntimeContext` (not in LLM-visible args)
- Persist analyses (embed `title + content`), recommendations (M:N analyses), RAG search
- User context, portfolio positions with **gain/loss %**, index get/create/list

**Non-Goals:**

- Wiring tools onto PM or sub-agent classes
- `DeepAgentFactory` tool lists / autonomous scheduler
- Market data tools (`GetMarketPriceTool`, news, URL fetch) — stub price provider only
- Frontend or API changes

## Decisions

### 1. Tool directory layout

```
agentic/nam_agentic/tools/
├── base.py
├── registry.py
├── schemas/
│   ├── memory.py
│   └── portfolio.py
├── memory/
│   ├── create_analysis.py
│   ├── create_recommendation.py
│   └── search_past_analyses.py
├── portfolio/
│   ├── get_user_context.py
│   ├── get_positions.py
│   ├── create_index.py
│   ├── get_index.py
│   └── list_indices.py
└── services/
    ├── embedding.py
    ├── analysis_search.py
    └── market_price.py      # protocol + stub + FakeMarketPriceProvider (tests)
```

### 2. Runtime context injection (`user_id`)

Tools are constructed with `(session_factory, user_id: UUID, ...services)`.

`ToolRegistry` receives `NamRuntimeContext` (or `user_id`) at build time and binds it into each tool instance. The LangChain `@tool` args schema **excludes `user_id`** — the singleton user comes from runtime context (`settings.default_user_id` or invoke context).

Tests pass `user_id` explicitly via tool constructor.

### 3. Pydantic schemas — domain enums from `nam_db.enums`

| Tool | LLM-visible input (no `user_id`) |
|------|----------------------------------|
| `CreateAnalysisTool` | `SubAgentRole`, `AnalysisTrigger`, optional `index_id`, `title`, `content` |
| `CreateRecommendationTool` | `analysis_ids`, `RecommendationType`, `content` |
| `SearchPastAnalysesTool` | `query`, `top_k`, optional `agent_filter`, `min_similarity` |
| `GetUserContextTool` | _(empty input)_ |
| `GetPortfolioPositionsTool` | _(empty input)_ |
| `CreateIndexTool` | `name`, `isin` |
| `GetIndexTool` | `index_id` or `isin` (validator: exactly one) |
| `ListIndicesTool` | optional `name_query: str \| None` — case-insensitive substring on `indices.name` |

No `Literal[...]` for domain values.

### 4. Embedding text (`CreateAnalysisTool` + consistency)

Canonical embed text:

```python
embed_text = f"{title}\n\n{content}"
```

Same string is stored in `content`; embedding vector derived from full title+body for better RAG retrieval.

### 5. `CreateRecommendationTool`

- Validate all `analysis_ids` exist for runtime `user_id`
- INSERT `recommendations` (`PENDING`, `agent=PORTFOLIO_MANAGER`) + junction rows
- **No `index_id` on input** — instrument context comes from linked analyses

### 6. RAG (`SearchPastAnalysesTool`)

pgvector cosine search, user-scoped, optional `AgentRole` filter. Query embedded via `EmbeddingService`. Results include `title`, `content_snippet`, `similarity_score`.

### 7. Portfolio positions + gain/loss %

JOIN `positions` + `indices`. Price via injectable `MarketPriceProvider`:

- **Production v1**: `StubMarketPriceProvider` → all price fields `null`
- **Tests**: `FakeMarketPriceProvider` with configurable ISIN → price map to assert `gain_loss_pct` math

```python
gain_loss_pct = float((current_price - average_cost) / average_cost * 100)
```

### 8. Index catalog tools

- **`CreateIndexTool`**: UPSERT by ISIN (same validation as API)
- **`GetIndexTool`**: by `index_id` or `isin`
- **`ListIndicesTool`**: all indices ordered by name; when `name_query` provided (e.g. `"google"`), filter `WHERE name ILIKE '%google%'`

### 9. `GetUserContextTool`

SELECT `users` for runtime `user_id`. Output: `firstname`, `date_of_birth`, computed `age`, `strategy`, `goals` (matches `openspec.md` §9 `GetUserContextTool`).

### 10. `ToolRegistry`

```python
class ToolRegistry:
    def __init__(self, session_factory, context: NamRuntimeContext, ...): ...
    def all_tools(self) -> list[BaseTool]: ...
```

Returns all eight tools. **No `pm_tools()` / `subagent_tools()`** — assignment is a later change.

### 11. Session and errors

- Async session per invocation; commit on write
- `ToolError` or `ValueError` with clear message for agent consumption
- Embedding dimension guard: `len(vec) == settings.embedding_dim`

## Risks / Trade-offs

- **[Risk] PnL null in prod until market tools** → stub + tested via fake provider
- **[Risk] Ollama unavailable in CI** → mock `EmbeddingService`
- **[Trade-off] No agent wiring** → tools exist but agents still return `[]` until follow-up

## Migration Plan

1. Implement tools + registry
2. No DB migration
3. `just test` green with mocked embed + fake prices

## Open Questions

- None blocking.
