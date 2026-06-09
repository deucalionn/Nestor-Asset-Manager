## Requirements

### Requirement: Index Pydantic schemas
The API MUST define Pydantic v2 schemas in `nam_api/schemas/index.py`:

- `IndexCreate`: `name` (str, min 1), `isin` (str, max 12), `index_type` (IndexType, required), optional `boursorama_ticker` (str, max 32), optional `yahoo_symbol` (str, max 32)
- `IndexRead`: `id`, `name`, `isin`, `index_type`, `boursorama_ticker`, `yahoo_symbol`, `created_at` with `model_config = ConfigDict(from_attributes=True)`

#### Scenario: Schema validation
- **WHEN** `IndexCreate(name="CAC 40", isin="FR0003500008", index_type=COMPANY)` is constructed without optional tickers
- **THEN** validation succeeds
- **AND** `yahoo_symbol` defaults to omitted/null

#### Scenario: Create index with Yahoo symbol
- **WHEN** `IndexCreate(name="Air Liquide", isin="FR0000120073", index_type=COMPANY, yahoo_symbol="AI.PA")` is constructed
- **THEN** validation succeeds

#### Scenario: Read model includes yahoo_symbol
- **WHEN** an index row with `yahoo_symbol="CW8.PA"` is serialized to `IndexRead`
- **THEN** `yahoo_symbol` is `"CW8.PA"`

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

### Requirement: Index catalog endpoints
The API MUST expose index catalog operations under `/indices`.

| Method | Route | Request | Response |
|--------|-------|---------|----------|
| GET | `/indices` | — | `list[IndexRead]` |
| POST | `/indices` | `IndexCreate` | `IndexRead` (201) |
| GET | `/indices/{index_id}` | — | `IndexRead` |

Route handlers MUST be `async def` and delegate to `IndexService` only.

#### Scenario: Create index
- **WHEN** `POST /indices` is called with `{name, isin, index_type}` and optional `boursorama_ticker` and optional `yahoo_symbol`
- **THEN** response status is 201
- **AND** the body includes `id`, `name`, `isin`, `index_type`, `boursorama_ticker`, `yahoo_symbol`, `created_at`

#### Scenario: Create ETF index
- **WHEN** `POST /indices` is called with `index_type=ETF` for a tracker ISIN
- **THEN** response status is 201
- **AND** `index_type` in the body is `ETF`

#### Scenario: List indices
- **WHEN** `GET /indices` is called
- **THEN** response status is 200
- **AND** each item includes `index_type`, `boursorama_ticker`, and `yahoo_symbol` (each nullable)

#### Scenario: Get index by id
- **WHEN** `GET /indices/{index_id}` is called for an existing index
- **THEN** response status is 200
- **AND** body includes `yahoo_symbol`

#### Scenario: Duplicate ISIN
- **WHEN** `POST /indices` is called with an ISIN that already exists
- **THEN** response status is 409

### Requirement: Index service tests
`api/tests/` MUST include async tests for `IndexService` covering create, list, get, duplicate ISIN, and optional `yahoo_symbol`.

#### Scenario: TDD coverage
- **WHEN** `just test` runs
- **THEN** index service tests pass
