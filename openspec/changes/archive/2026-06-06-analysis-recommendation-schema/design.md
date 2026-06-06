# Design — analysis & recommendation schema

## Context

Portfolio core (`users`, `indices`, `transactions`, `positions`) is implemented. `analysis.py` and `recommendation.py` are empty stubs. Enums `AgentRole`, `SubAgentRole`, `RecommendationType`, and `RecommendationStatus` already exist in `nam_db/enums.py`. Agent runtime accepts events but does not persist analyses yet.

**Agent roles (from architecture diagram):**

```text
                    Portfolio Manager
                   (recommendations only)
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
  Sector Analyst    Macro Strategist    ETF/Quant Specialist
     (analyses)        (analyses)           (analyses)
```

Sub-agents write **analyses** (detailed reports, vectorized for RAG). The PM reads selected analyses and writes **recommendations** (actionable BUY/HOLD/SELL proposals). The human user resolves recommendations via the API — agents never touch `transactions`.

## Goals / Non-Goals

**Goals:**

- Persist analyses with semantic embeddings for `search_past_analyses` (future tool)
- Persist recommendations with lifecycle status and optional user comment
- Link recommendations to **one or many** source analyses via junction table
- Expose read + feedback API for the frontend
- Keep agent write path ready (agentic services import `nam_db` models directly — no HTTP)

**Non-Goals:**

- `CreateAnalysisTool` / `CreateRecommendationTool` implementation (follow-up change)
- Deep Agents factory wiring
- Frontend UI for analyses/recommendations
- Embedding generation logic in API (computed in agentic when tools land)
- News ingestion table (trigger enum captures *how* the run started, not raw payload)

## Decisions

### 1. Many-to-many: `recommendation_analyses`

**Decision:** Junction table with composite PK `(recommendation_id, analysis_id)`.

**Rationale:** PM may synthesize several sub-agent reports into one recommendation. An analysis may inform zero or one recommendation (typically one, but schema does not forbid reuse).

**Alternative rejected:** Single `analysis_id` on `recommendations` (current `openspec.md`) — too restrictive.

### 2. `AnalysisTrigger` enum (not JSON metadata)

**Decision:** PostgreSQL enum `analysis_trigger_enum`:

| Value | Meaning |
|-------|---------|
| `MARKET_SESSION` | APScheduler market phase (EU/US/ASIA) |
| `NEWS_EVENT` | Inbound news/event bus notification |
| `MANUAL` | User-initiated (future chat or UI) |
| `TASK` | PM delegated a sub-agent task |

**Rationale:** Filterable, indexable, autogenerate-friendly via `alembic-postgresql-enum`. Raw news payload stays in agent workspace or future table.

### 3. Analysis fields: `title`, `index_id`, `content`, embedding

| Column | Notes |
|--------|-------|
| `title` | VARCHAR(255) NOT NULL — short label for UI and RAG snippets |
| `index_id` | UUID FK → `indices.id`, **nullable** — set when analysis targets a specific instrument |
| `content` | TEXT NOT NULL — full agent report |
| `content_embedding` | `vector(384)` NOT NULL — matches `embedding_dim` in agentic settings (`nomic-embed-text`) |
| `agent` | `agent_enum` NOT NULL — authoring agent role |
| `trigger` | `analysis_trigger_enum` NOT NULL |

**Index:** HNSW on `content_embedding` (cosine) + btree on `(user_id, created_at)` and `(user_id, index_id)`.

### 4. Recommendation fields

| Column | Notes |
|--------|-------|
| `agent` | `agent_enum` NOT NULL — always `PORTFOLIO_MANAGER` in practice |
| `content` | TEXT NOT NULL — PM synthesis / rationale (not a copy of analysis bodies) |
| `type` | `recommendation_type_enum` — BUY / HOLD / SELL |
| `status` | `recommendation_status_enum`, default `PENDING` |
| `user_comment` | TEXT NULL — feedback when applying or rejecting |
| `resolved_at` | TIMESTAMPTZ NULL — set when status becomes APPLIED or REJECTED |

No `analysis_id` column — use `recommendation_analyses`.

### 5. SubAgentRole (tool input) vs AgentRole (DB column)

**This is a Python type-safety boundary, not two different database values.**

- PostgreSQL has one enum: `agent_enum` with all four `AgentRole` values (including `PORTFOLIO_MANAGER`).
- **`AgentRole`** is used on ORM columns (`analyses.agent`, `recommendations.agent`) — what gets stored.
- **`SubAgentRole`** is a **subset enum** (excludes PM) used only on future **`CreateAnalysisTool`** input validation — so the PM cannot accidentally call "create analysis" on itself; only sector/macro/ETF sub-agents can author analyses.

Both enums share the same string values for the three sub-agents (`SECTOR_ANALYST`, etc.). Flow:

```text
CreateAnalysisTool(agent=SubAgentRole.SECTOR_ANALYST)
        → persisted as AgentRole.SECTOR_ANALYST in analyses.agent
```

`CreateRecommendationTool` will accept only `AgentRole.PORTFOLIO_MANAGER`.

### 6. Write boundaries

| Writer | Tables |
|--------|--------|
| **nam-agentic** (future tools) | INSERT `analyses`, INSERT `recommendations` + junction rows |
| **nam-api** | SELECT analyses/recommendations; UPDATE recommendation status/comment only |
| **nam-api** | NEVER INSERT analyses or recommendations in v1 |

### 7. API surface (v1)

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/analyses` | List user analyses (newest first), optional `index_id` filter |
| GET | `/analyses/{id}` | Detail |
| GET | `/recommendations` | List with nested analysis IDs/titles |
| GET | `/recommendations/{id}` | Detail with linked analyses |
| PATCH | `/recommendations/{id}` | Set `status` (APPLIED/REJECTED), optional `user_comment` |

Single-user v1: same pattern as portfolio — implicit `default_user_id` from settings.

## Risks / Trade-offs

- **[Risk] Embedding dimension mismatch** → Hard-code 384 in migration; validate against `EMBEDDING_DIM` in agentic settings doc.
- **[Risk] Vector index build time on empty table** → Acceptable in dev; tune HNSW params later.
- **[Risk] M:N without ordering** → Junction has no `rank` column in v1; PM synthesis order is implicit in recommendation `content`. Add `position` column later if needed.
- **[Trade-off] No soft-delete on analyses** → Hard delete deferred; analyses are append-only audit trail.

## Migration Plan

1. New Alembic revision `analysis_recommendation` depending on `portfolio_core`
2. `CREATE TYPE` for `analysis_trigger_enum`, existing agent/recommendation enums if not yet in DB (agent enums may need first creation in this migration)
3. Create tables + FKs + indexes
4. `alembic upgrade head` via `just migrate`
5. Rollback: `alembic downgrade -1`

## Open Questions

- None blocking v1 — semantic search RPC can be raw SQL in agentic tool when tools are implemented.
