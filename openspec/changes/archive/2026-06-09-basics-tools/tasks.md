# Tasks — basics-tools

## 1. Schemas & shared services

- [x] 1.1 Add `nam_agentic/tools/schemas/memory.py` — inputs/outputs without `user_id`; `CreateAnalysisInput/Output`, `CreateRecommendationInput/Output`, `SearchPastAnalysesInput`, `AnalysisSearchResult`
- [x] 1.2 Add `nam_agentic/tools/schemas/portfolio.py` — `UserContextOutput`, `PositionItem` (`gain_loss_pct`), `GetPortfolioPositionsOutput`, index schemas, `ListIndicesInput`, `IndexListItem`
- [x] 1.3 Implement runtime binding helper — inject `user_id` from `NamRuntimeContext` into tool constructors; exclude from LangChain args schema
- [x] 1.4 Implement `nam_agentic/tools/services/embedding.py` — Ollama client, dimension guard, canonical `title\n\ncontent` helper
- [x] 1.5 Implement `nam_agentic/tools/services/analysis_search.py` — pgvector cosine query
- [x] 1.6 Implement `MarketPriceProvider` protocol + `StubMarketPriceProvider` + `FakeMarketPriceProvider` for tests

## 2. Memory tools

- [x] 2.1 Implement `CreateAnalysisTool` — SubAgentRole validation, embed title+content, INSERT `analyses`
- [x] 2.2 Implement `CreateRecommendationTool` — validate analysis ownership, INSERT recommendation + junction, `PENDING` only (no `index_id` input)
- [x] 2.3 Implement `SearchPastAnalysesTool` — embed query, ranked snippets

## 3. Portfolio & context tools

- [x] 3.1 Implement `GetUserContextTool` — SELECT user profile, computed `age`
- [x] 3.2 Implement `GetPortfolioPositionsTool` — JOIN positions/indices, `gain_loss_pct` via price provider
- [x] 3.3 Implement `CreateIndexTool` — ISIN UPSERT
- [x] 3.4 Implement `GetIndexTool` — lookup by `index_id` or `isin`
- [x] 3.5 Implement `ListIndicesTool` — optional `name_query` ILIKE filter (e.g. `"google"`)

## 4. Registry

- [x] 4.1 Expand `ToolRegistry` — construct all eight tools with runtime context, expose `all_tools()`
- [x] 4.2 Wire registry construction in app bootstrap (session factory + default context) — no agent `tools()` assignment

## 5. Tests

- [x] 5.1 Add agentic test fixtures (session factory, mock embedding, fake price provider, user/index/analysis factories)
- [x] 5.2 Tool tests: `CreateAnalysisTool`, `CreateRecommendationTool`
- [x] 5.3 Tool tests: `SearchPastAnalysesTool` (isolation, ordering)
- [x] 5.4 Tool tests: `GetUserContextTool`, `GetPortfolioPositionsTool` (gain_loss_pct with fake prices)
- [x] 5.5 Tool tests: `CreateIndexTool`, `GetIndexTool`, `ListIndicesTool` (name search)
- [x] 5.6 Verify LangChain tool schemas exclude `user_id`
- [x] 5.7 Integrate agentic tests into Docker harness; `just test` green

## 6. Documentation

- [x] 6.1 Update `openspec.md` §9 tool catalog at archive if needed (`ListIndicesTool`, runtime `user_id` pattern)
