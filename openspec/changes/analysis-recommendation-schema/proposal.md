# Analysis & recommendation schema

## Why

Sub-agents produce textual **analyses**; the Portfolio Manager synthesizes them into **recommendations** the user accepts or rejects. Without persisted models, pgvector embeddings, and a many-to-many link between analyses and recommendations, neither RAG nor the human-in-the-loop workflow can exist. This must land **before** Deep Agents tools and agent wiring.

## What Changes

- Implement `Analysis` and `Recommendation` SQLAlchemy models (replacing stubs)
- Add `AnalysisTrigger` enum (what caused the analysis run)
- Add `title` (short label), optional `index_id`, `content`, `content_embedding vector(384)` on analyses
- Replace single `analysis_id` FK on recommendations with **`recommendation_analyses`** junction table (M:N)
- Alembic migration: new PostgreSQL enums, tables, indexes (including vector index on embeddings)
- API read endpoints for analyses and recommendations; user feedback endpoint to set recommendation status (`PENDING` → `APPLIED` | `REJECTED`)
- **BREAKING (spec only)**: `openspec.md` §4.3.6 drops `recommendations.analysis_id` in favour of the junction table

## Capabilities

### New Capabilities

- `analysis-recommendation-schema`: ORM models, enums, migration, relationships, agent write boundary
- `api-analyses-recommendations`: REST list/detail for analyses & recommendations; PATCH status + `user_comment`

### Modified Capabilities

- `shared-db-package`: `analysis` and `recommendation` modules are fully implemented ORM models, not stubs

## Impact

| Area | Impact |
|------|--------|
| `packages/db/` | Models, enums, Alembic revision, `__init__.py` exports |
| `api/` | New schemas, services, routers; no agent write endpoints |
| `agentic/` | No Deep Agent wiring yet — tools come in a follow-up change |
| `openspec.md` | §4.1 ERD, §4.3.5–4.3.6 updated after implementation |
| PostgreSQL | New enums, `analyses`, `recommendations`, `recommendation_analyses`; pgvector column |
