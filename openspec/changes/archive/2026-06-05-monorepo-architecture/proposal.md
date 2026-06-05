## Why

NAM has a fully documented architecture (`openspec.md`) but no executable project structure. Before implementing agents, tools, or API endpoints, we need a **uv-based Python monorepo** with shared database models, isolated packages, and clear dependency boundaries — so `api/` and `agentic/` can evolve independently while sharing a single PostgreSQL schema.

## What Changes

- Initialize **uv workspace** at repo root with three packages: `nam-db`, `nam-api`, `nam-agentic`
- Scaffold `packages/db/` with SQLAlchemy 2.0 async base, shared enums, Alembic, and empty model modules
- Scaffold `api/` with FastAPI app skeleton, router layout, and dependency on `nam-db` + `nam-agentic`
- Scaffold `agentic/` with Deep Agents OOP layout (agents, tools, prompts, scheduler, factory, runner)
- Add **docker-compose** for local PostgreSQL + pgvector (dev infra only)
- Add root-level dev tooling: `.env.example`, `justfile` (dev commands), README
- Add **no business logic** in this change — structure and wiring only

## Capabilities

### New Capabilities

- `monorepo-workspace`: uv workspace root, inter-package dependencies, dev commands
- `shared-db-package`: `nam-db` — enums, SQLAlchemy base, session factory, Alembic config, model stubs
- `api-package`: `nam-api` — FastAPI skeleton, health endpoint, package layout
- `agentic-package`: `nam-agentic` — OOP agent/tool/prompt/scheduler skeleton, DeepAgentFactory stub
- `dev-infrastructure`: docker-compose PostgreSQL+pgvector (auto-init), `justfile`, `.env.example`

### Modified Capabilities

- _(none — greenfield repo, no existing specs in `openspec/specs/`)_

## Impact

- **New directories**: `packages/db/`, `api/`, `agentic/`, root `pyproject.toml`
- **Dependencies**: uv, FastAPI, SQLAlchemy 2.0, Alembic (async template), alembic-postgresql-enum, pydantic v2, deepagents, APScheduler
- **No API contract changes** — no endpoints beyond `/health` stub
- **No database migrations with data** — Alembic initialized, initial migration deferred to next change
- **Reference**: all structural decisions must align with `openspec.md` v0.2.0
