## Why

The agentic module needs a real portfolio in PostgreSQL to read positions and indices via tools, but `nam-api` today only exposes `/health` and `nam_db` models are stubs. Before investing in Deep Agents, the API must own the portfolio domain: indices catalog, transactions, and derived position snapshots — implemented async, test-first (Docker + pgvector), with clear router/service separation.

## What Changes

- Implement SQLAlchemy models + initial Alembic migration for `users`, `indices`, `transactions`, `positions`
- Add async **services** in `nam_api/services/`:
  - `IndexService` — create, get, list indices
  - `TransactionService` — **create, update, delete** transactions (+ triggers position recalc)
  - `PositionService` — recalculate snapshots; list positions for a user
  - `PositionCalculator` — pure ACB math (no DB)
- Add async **routers** (thin — delegate to services)
- Add Pydantic v2 **schemas**
- **TDD via Docker** (pattern from AImmo `back-end-services`): `docker/tests/docker-compose.test.yml` with `pgvector/pgvector:pg16`, test-runner runs `alembic upgrade head && pytest`
- All DB I/O and route handlers use `async def` + `AsyncSession`

**Not in this change:** auth, analyses, recommendations, WebSocket chat, agentic tools wiring.

**Transaction edit:** Direct UPDATE/DELETE on `transactions` via `TransactionService` (not a separate correction service). Positions are always rebuilt from the ledger after any mutation. _(Updates `openspec.md` ledger immutability rule — see design D3.)_

## Capabilities

### New Capabilities

- `portfolio-schema`: ORM models and migration for `users`, `indices`, `transactions`, `positions`
- `api-indices`: Index catalog service + REST routes
- `api-transactions-positions`: Transaction CRUD, position recalculation, portfolio read APIs

### Modified Capabilities

- _(none at archive level; `openspec.md` §4.3.3 ledger rule updated during apply)_

## Impact

| Area | Impact |
|------|--------|
| **Module** | `packages/db`, `api/`, `docker/tests/` |
| **Tables** | `users`, `indices`, `transactions`, `positions` |
| **Agentic** | No writes — read-only later via tools |
| **PostgreSQL** | pgvector extension required in test compose (same image as dev) |
| **Tests** | Docker-only (`just test` runs all of `api/tests`, including `PositionCalculator` unit tests) |
