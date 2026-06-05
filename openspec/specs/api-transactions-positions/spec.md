## ADDED Requirements

### Requirement: Typed route input and output
All transaction and position routes MUST declare explicit Pydantic request bodies and `response_model` on every endpoint.

#### Scenario: POST transaction typing
- **WHEN** `POST /users/{user_id}/transactions` succeeds
- **THEN** request body validates as `TransactionCreate`
- **AND** response validates as `TransactionRead`

#### Scenario: GET positions typing
- **WHEN** `GET /users/{user_id}/positions` succeeds
- **THEN** response validates as `list[PositionRead]`

### Requirement: Transaction and position Pydantic schemas
The API MUST define in `nam_api/schemas/`:

**`transaction.py`**
- `TransactionCreate`: `index_id`, `type: TransactionType`, `price > 0`, `quantity > 0`, `date`, optional `fees >= 0`
- `TransactionUpdate`: same fields as create, all optional (at least one required on update)
- `TransactionRead`: all persisted fields including `id`, `user_id`, `created_at`

**`position.py`**
- `PositionRead`: `id`, `user_id`, `index_id`, `quantity`, `average_cost`, `last_update`

Enums MUST be imported from `nam_db.enums`.

#### Scenario: BUY transaction payload
- **WHEN** `TransactionCreate` uses `type=TransactionType.BUY`
- **THEN** validation succeeds with positive `price` and `quantity`

### Requirement: PositionCalculator pure logic
`PositionCalculator` MUST implement ACB rules from `openspec.md`:

- BUY increases quantity and updates average cost (fees included in cost basis)
- SELL decreases quantity without changing ACB; fails if insufficient quantity
- Zero quantity yields no position (delete snapshot)

#### Scenario: Two buys then sell
- **GIVEN** BUY 10 @ 100 then BUY 10 @ 120
- **WHEN** position is computed via replay
- **THEN** quantity is 20 and average cost reflects weighted average including fees

#### Scenario: Oversell rejected
- **GIVEN** position quantity 5
- **WHEN** a SELL of 10 is applied in the calculator
- **THEN** an `InsufficientQuantityError` (or equivalent) is raised

### Requirement: TransactionService CRUD
`TransactionService` MUST expose async methods returning `TransactionRead` (not dicts):

- `create(session, user_id, data: TransactionCreate) -> TransactionRead`
- `update(session, user_id, transaction_id, data: TransactionUpdate) -> TransactionRead`
- `delete(session, user_id, transaction_id) -> None`
- `list_for_user(session, user_id) -> list[TransactionRead]`

Each mutating method MUST:
1. Verify `user_id` and related entities exist
2. Apply the SQL change (INSERT / UPDATE / DELETE on `transactions`)
3. Call `PositionService.recalculate_for_user_index` for affected index(es)
4. Run inside a single DB transaction boundary

#### Scenario: Create BUY transaction
- **WHEN** a valid BUY is created for a user
- **THEN** a new transaction row exists
- **AND** the user's position for that index reflects increased quantity

#### Scenario: Update transaction
- **WHEN** `TransactionService.update` changes a transaction's price
- **THEN** the transaction row is updated in place
- **AND** positions are recalculated from the full ledger

#### Scenario: Delete transaction
- **WHEN** `TransactionService.delete` removes a transaction
- **THEN** the row no longer exists
- **AND** positions are recalculated from the remaining ledger

### Requirement: PositionService
`PositionService` MUST provide:

- `async def list_for_user(session, user_id) -> list[PositionRead]`
- `async def recalculate_for_user_index(session, user_id, index_id) -> None` — replays ledger ordered by `date`, `created_at` using `PositionCalculator`

#### Scenario: List positions
- **WHEN** `GET /users/{user_id}/positions` is called
- **THEN** response status is 200
- **AND** body lists current position snapshots

### Requirement: Transaction and position routes
Routers MUST expose async endpoints with typed I/O:

| Method | Route | Request | Response |
|--------|-------|---------|----------|
| GET | `/users/{user_id}/transactions` | — | `list[TransactionRead]` |
| POST | `/users/{user_id}/transactions` | `TransactionCreate` | `TransactionRead` |
| PUT | `/users/{user_id}/transactions/{transaction_id}` | `TransactionUpdate` | `TransactionRead` |
| DELETE | `/users/{user_id}/transactions/{transaction_id}` | — | 204 No Content |
| GET | `/users/{user_id}/positions` | — | `list[PositionRead]` |

#### Scenario: Unknown user
- **WHEN** a portfolio route is called with a non-existent `user_id`
- **THEN** response status is 404

#### Scenario: Insufficient quantity on SELL
- **WHEN** a SELL exceeds held quantity after replay
- **THEN** response status is 422 with an error detail

### Requirement: Async-only handlers and services
All portfolio route handlers and service methods MUST be declared with `async def` and use `AsyncSession`.

#### Scenario: Async route inspection
- **WHEN** portfolio router modules are reviewed
- **THEN** every endpoint function is `async def`

### Requirement: Docker-based integration tests
Integration and API tests MUST run inside Docker Compose (AImmo pattern):

- `docker/tests/docker-compose.test.yml` with `pgvector/pgvector:pg16` and a `test-runner` service
- Test runner executes `alembic upgrade head && pytest api/tests`
- `DATABASE_URL` in `.env.test` points to the compose `db` service

#### Scenario: just test
- **WHEN** `just test` is run from the repo root
- **THEN** Docker starts pgvector Postgres and the test-runner container
- **AND** all service and API tests pass

### Requirement: Unit tests for PositionCalculator
`PositionCalculator` unit tests live under `api/tests/unit/` and MUST be included in the Docker test run (`just test`).

#### Scenario: Calculator tests in Docker
- **WHEN** `just test` runs
- **THEN** `api/tests/unit/test_position_calculator.py` passes inside the test-runner container

### Requirement: Agent write boundary
Portfolio services MUST only be invoked from `nam-api` — not from `nam-agentic` in this change.

#### Scenario: No agentic imports
- **WHEN** `agentic/` is searched for `TransactionService`
- **THEN** none are found
