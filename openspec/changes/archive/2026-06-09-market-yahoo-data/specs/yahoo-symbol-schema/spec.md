## ADDED Requirements

### Requirement: indices.yahoo_symbol column
`nam_db` MUST add a nullable `yahoo_symbol` column on `indices`.

| Column | Type | Constraints |
|--------|------|-------------|
| `yahoo_symbol` | str(32) | nullable |

The column stores the Yahoo Finance ticker (e.g. `AI.PA`, `CW8.PA`). It is **metadata cache only** — same role as `boursorama_ticker`, not a separate financial entity.

Agents MAY auto-persist via `YahooIndexResolver`; users MAY set via API or `update_index_yahoo_symbol`.

There MUST be **no** automatic mapping from `boursorama_ticker` to `yahoo_symbol`.

#### Scenario: Migration adds column with null default
- **WHEN** the Alembic migration runs on a database with existing indices
- **THEN** all existing rows have `yahoo_symbol = NULL`
- **AND** portfolio and index tools continue to work

#### Scenario: Manual symbol persisted
- **WHEN** `update_index_yahoo_symbol` or `POST /indices` supplies `yahoo_symbol="AI.PA"`
- **THEN** the row stores the value
- **AND** subsequent resolution returns `resolved_from_db=true` without yfinance Lookup

### Requirement: Index ORM exposes yahoo_symbol
The SQLAlchemy `Index` model MUST map `yahoo_symbol: Mapped[str | None]` with `String(32), nullable=True`.

#### Scenario: Model attribute readable
- **WHEN** an index row with `yahoo_symbol="CW8.PA"` is loaded
- **THEN** `index.yahoo_symbol == "CW8.PA"`
