> **Roadmap**: `monorepo-architecture` → **api-portfolio-core** → `deep-agent-core`

> **Approach**: TDD — red → green. All `api/tests` **Docker only** via `just test` (pgvector Postgres).

## 1. Docker test infrastructure (AImmo pattern)

- [x] 1.1 Create `docker/tests/docker-compose.test.yml` — `pgvector/pgvector:pg16` + `test-runner`
- [x] 1.2 Create `docker/tests/Dockerfile.test` — uv sync, copy monorepo, `CMD alembic upgrade head && pytest api/tests -svv`
- [x] 1.3 Create `.env.test` — `DATABASE_URL=postgresql+asyncpg://nam:nam@db:5432/nam_test`
- [x] 1.4 Add `just test` — `docker compose -f docker/tests/docker-compose.test.yml up --build --abort-on-container-exit`
- [x] 1.5 Add `just test-down` — compose down -v --remove-orphans
- [x] 1.6 Document Docker test workflow in README

## 2. Pytest fixtures (`api/tests/`)

- [x] 2.1 Add deps: `httpx`, `pytest`, `pytest-asyncio` to `api/pyproject.toml`
- [x] 2.2 Create `api/tests/conftest.py` — `setup_db`, `db_session` (truncate per test), `async_client` (AImmo-style overrides)
- [x] 2.3 Create `api/tests/factories.py` — `UserFactory` (with `date_of_birth`), `IndexFactory`

## 3. Portfolio schema (`nam-db`)

- [x] 3.1 Implement `User` model — `date_of_birth: DATE`, no `age` column
- [x] 3.2 Implement `Index` model — `nam_db/models/index.py`
- [x] 3.3 Implement `Transaction` model — with strategic indexes (`user_id`, `user_id+date`, `user_id+index_id`)
- [x] 3.4 Implement `Position` model — index on `user_id`, unique `(user_id, index_id)`
- [x] 3.5 Export models from `nam_db/models/__init__.py` for Alembic
- [x] 3.6 Autogenerate migration `portfolio_core`, review enums/FKs/checks/**indexes**
- [x] 3.7 Verify migration in Docker test runner

## 4. PositionCalculator (unit tests first — TDD, run in Docker with the rest)

- [x] 4.1 Write `api/tests/unit/test_position_calculator.py` (failing)
- [x] 4.2 Implement `nam_api/services/position_calculator.py`
- [x] 4.3 Green unit tests via `just test`

## 5. Pydantic schemas + exceptions

- [x] 5.1 `nam_api/schemas/index.py` — Create + Read
- [x] 5.2 `nam_api/schemas/transaction.py` — Create, Update, Read
- [x] 5.3 `nam_api/schemas/position.py` — Read
- [x] 5.4 `nam_api/schemas/user.py` — Create + Read with computed `age` from `date_of_birth`
- [x] 5.5 `nam_api/exceptions.py` + HTTP mapping helper
- [x] 5.6 All routers: explicit `response_model=` on every endpoint (input body + output typed)

## 6. IndexService + routes (TDD in Docker)

- [x] 6.1 Write `api/tests/services/test_index_service.py`
- [x] 6.2 Implement `nam_api/services/index_service.py`
- [x] 6.3 Write `api/tests/api/test_indices.py`
- [x] 6.4 Implement `nam_api/routers/indices.py` + register in `main.py`
- [x] 6.5 Green via `just test`

## 7. TransactionService + PositionService (TDD in Docker)

- [x] 7.1 Write `api/tests/services/test_transaction_service.py` — create, update, delete
- [x] 7.2 Implement `nam_api/services/transaction_service.py`
- [x] 7.3 Implement `nam_api/services/position_service.py` (uses `PositionCalculator`)
- [x] 7.4 Test insufficient SELL → 422
- [x] 7.5 Test update recalculates positions; test delete recalculates
- [x] 7.6 Green service tests in Docker

## 8. Transaction + position routes (TDD in Docker)

- [x] 8.1 Write `api/tests/api/test_transactions.py`
- [x] 8.2 Write `api/tests/api/test_positions.py`
- [x] 8.3 Implement `nam_api/routers/transactions.py`, `positions.py`
- [x] 8.4 Wire dependency injection for `AsyncSession` in FastAPI
- [x] 8.5 Green all tests via `just test`

## 9. openspec.md alignment

- [x] 9.1 Update `openspec.md` §4.3.1 — `date_of_birth` replaces `age`
- [x] 9.2 Update `openspec.md` §4.3.3 — transactions mutable via API
- [x] 9.3 Update ledger immutability requirement → API-owned CRUD + position recalc

## 10. Verification

- [x] 10.1 `just test` — all green in Docker
- [x] 10.2 `uv run ruff check api/ packages/db/`
- [x] 10.3 Manual smoke via dev compose: index → BUY → GET positions → PUT transaction → DELETE
