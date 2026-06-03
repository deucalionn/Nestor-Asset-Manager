## ADDED Requirements

### Requirement: Index Pydantic schemas
The API MUST define Pydantic v2 schemas in `nam_api/schemas/index.py`:

- `IndexCreate`: `name` (str, min 1), `isin` (str, max 12)
- `IndexRead`: `id`, `name`, `isin`, `created_at` with `model_config = ConfigDict(from_attributes=True)`

#### Scenario: Schema validation
- **WHEN** `IndexCreate(name="CAC 40", isin="FR0003500008")` is constructed
- **THEN** validation succeeds

### Requirement: Typed route input and output
All index routes MUST use explicit Pydantic types for request bodies and `response_model` on responses — no untyped dict returns.

#### Scenario: POST /indices response typing
- **WHEN** `POST /indices` succeeds
- **THEN** the handler declares `response_model=IndexRead`
- **AND** the request body is validated as `IndexCreate`

#### Scenario: GET /indices response typing
- **WHEN** `GET /indices` succeeds
- **THEN** the handler declares `response_model=list[IndexRead]`

### Requirement: IndexService async API
`IndexService` MUST expose async methods returning Pydantic read models:

- `create(session, data: IndexCreate) -> IndexRead`
- `get(session, index_id: UUID) -> IndexRead`
- `list(session) -> list[IndexRead]`

All methods MUST use `AsyncSession` and `async def`.

#### Scenario: Create index
- **WHEN** `IndexService.create` is called with valid data
- **THEN** a row is inserted into `indices`
- **AND** the returned value is an `IndexRead` instance

### Requirement: Index routes
Routers MUST expose:

| Method | Route | Request | Response |
|--------|-------|---------|----------|
| GET | `/indices` | — | `list[IndexRead]` |
| POST | `/indices` | `IndexCreate` | `IndexRead` (201) |
| GET | `/indices/{index_id}` | — | `IndexRead` |

Route handlers MUST be `async def` and delegate to `IndexService` only.

#### Scenario: List indices
- **WHEN** `GET /indices` is called
- **THEN** response status is 200
- **AND** body validates against `list[IndexRead]`

#### Scenario: Duplicate ISIN
- **WHEN** `POST /indices` is called with an ISIN that already exists
- **THEN** response status is 409

### Requirement: Index service tests
`api/tests/` MUST include async tests for `IndexService` covering create, list, get, and duplicate ISIN.

#### Scenario: TDD coverage
- **WHEN** `just test` runs
- **THEN** index service tests pass
