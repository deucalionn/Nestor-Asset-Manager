## ADDED Requirements

### Requirement: Index yahoo_symbol field on API schemas
`nam_api/schemas/index.py` MUST extend index schemas:

- `IndexCreate`: optional `yahoo_symbol: str | None` (max 32)
- `IndexRead`: `yahoo_symbol: str | None`

Existing fields (`index_type`, `boursorama_ticker`) MUST remain unchanged.

#### Scenario: Create index with Yahoo symbol
- **WHEN** `IndexCreate(name="Air Liquide", isin="FR0000120073", index_type=COMPANY, yahoo_symbol="AI.PA")` is constructed
- **THEN** validation succeeds

#### Scenario: Read model includes yahoo_symbol
- **WHEN** an index row with `yahoo_symbol="CW8.PA"` is serialized to `IndexRead`
- **THEN** `yahoo_symbol` is `"CW8.PA"`

## MODIFIED Requirements

### Requirement: Index Pydantic schemas
The API MUST define Pydantic v2 schemas in `nam_api/schemas/index.py`:

- `IndexCreate`: `name` (str, min 1), `isin` (str, max 12), `index_type` (IndexType, required), optional `boursorama_ticker` (str, max 32), optional `yahoo_symbol` (str, max 32)
- `IndexRead`: `id`, `name`, `isin`, `index_type`, `boursorama_ticker`, `yahoo_symbol`, `created_at` with `model_config = ConfigDict(from_attributes=True)`

#### Scenario: Schema validation
- **WHEN** `IndexCreate(name="CAC 40", isin="FR0003500008", index_type=COMPANY)` is constructed without optional tickers
- **THEN** validation succeeds
- **AND** `yahoo_symbol` defaults to omitted/null

### Requirement: Index catalog endpoints
The API MUST expose index catalog operations under `/indices`.

#### Scenario: Create index
- **WHEN** `POST /indices` is called with `{name, isin, index_type}` and optional `boursorama_ticker` and optional `yahoo_symbol`
- **THEN** response status is 201
- **AND** the body includes `id`, `name`, `isin`, `index_type`, `boursorama_ticker`, `yahoo_symbol`, `created_at`

#### Scenario: List indices
- **WHEN** `GET /indices` is called
- **THEN** response status is 200
- **AND** each item includes `index_type`, `boursorama_ticker`, and `yahoo_symbol` (each nullable)

#### Scenario: Get index by id
- **WHEN** `GET /indices/{index_id}` is called for an existing index
- **THEN** response status is 200
- **AND** body includes `yahoo_symbol`
