## MODIFIED Requirements

### Requirement: Index catalog endpoints
The API MUST expose index catalog operations under `/indices`.

#### Scenario: Create index
- **WHEN** `POST /indices` is called with `{name, isin, index_type}` and optional `boursorama_ticker`
- **THEN** response status is 201
- **AND** the body includes `id`, `name`, `isin`, `index_type`, `boursorama_ticker`, `created_at`

#### Scenario: Create ETF index
- **WHEN** `POST /indices` is called with `index_type=ETF` for a tracker ISIN
- **THEN** response status is 201
- **AND** `index_type` in the body is `ETF`

#### Scenario: List indices
- **WHEN** `GET /indices` is called
- **THEN** response status is 200
- **AND** each item includes `index_type` and `boursorama_ticker` (nullable)
