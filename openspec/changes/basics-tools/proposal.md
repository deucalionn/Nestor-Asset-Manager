## Why

The agent runtime skeleton (`DeepAgentFactory`, `ToolRegistry`, subagent classes) is in place, and the database layer for analyses, recommendations, positions, and indices is implemented — but agents have **no executable tools** yet. Without typed tools that read/write PostgreSQL and query pgvector, Deep Agents cannot persist analyses, synthesize recommendations, inspect the portfolio, or leverage semantic memory.

This change delivers the **first production tool set**. Tool **assignment** to PM vs sub-agents is a separate follow-up — here we only implement and register the tools.

## What Changes

- Implement eight core tools as OOP classes under `agentic/nam_agentic/tools/`:
  - **Memory**: `CreateAnalysisTool`, `CreateRecommendationTool`, `SearchPastAnalysesTool` (RAG)
  - **Portfolio & context**: `GetUserContextTool`, `GetPortfolioPositionsTool` (gain/loss %), `CreateIndexTool`, `GetIndexTool`, `ListIndicesTool` (optional name search)
- Strongly typed Pydantic v2 input/output schemas per tool (`nam_agentic/tools/schemas/`)
- **`user_id` injected from `NamRuntimeContext` at tool bind time** — not exposed in LangChain tool args (avoids LLM UUID hallucination)
- Shared services: `EmbeddingService` (Ollama `nomic-embed-text`, dim 384), pgvector search helper, `MarketPriceProvider` (stub + test fake)
- Extend `ToolRegistry` to instantiate all tools and expose `all_tools()` — no agent wiring in this change
- Agentic unit/integration tests per tool (Docker Postgres, mocked embeddings)

**Non-breaking** for API — agents write directly to `nam_db`; no new HTTP routes.

## Capabilities

### New Capabilities

- `agentic-basics-tools`: Typed tool implementations for user context, analysis/recommendation persistence, RAG search, portfolio positions with PnL %, and index catalog access

### Modified Capabilities

- `agentic-package`: `ToolRegistry` must instantiate and expose all basics-tools (registry only — not agent assignment)

## Impact

| Area | Impact |
|------|--------|
| `agentic/nam_agentic/tools/` | New modules: `memory/`, `portfolio/`, `schemas/`, `services/` |
| `agentic/nam_agentic/tools/registry.py` | Full registry — `all_tools()` |
| `agentic/` tests | New tool test suite |
| `packages/db` | Read/write only — no schema migration |
| External | Ollama embedding API for analysis create + RAG search |

**Out of scope:** assigning tools to `PortfolioManagerAgent` / subagents, scheduler wiring, market-data tools.
