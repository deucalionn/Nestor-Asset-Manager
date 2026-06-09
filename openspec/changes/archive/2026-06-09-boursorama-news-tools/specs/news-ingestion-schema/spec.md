## ADDED Requirements

### Requirement: NewsSource enum
`nam_db.enums` MUST define `NewsSource` with at least `BOURSORAMA`.

#### Scenario: Enum registered in PostgreSQL
- **WHEN** the Alembic migration runs
- **THEN** PostgreSQL type `newssource` exists with value `BOURSORAMA`

### Requirement: NewsCategory enum
`nam_db.enums` MUST define `NewsCategory` with values:

| Value | Use |
|-------|-----|
| `CALENDAR_GENERAL` | Main calendars index page |
| `CALENDAR_LISTED_COMPANIES` | Listed-company calendar |
| `CALENDAR_MACRO` | Macroeconomic calendar |
| `CALENDAR_DIVIDENDS` | Dividend calendar |
| `MARKETS` | Market news feed |
| `FINANCE` | Corporate finance news feed |
| `COMPANY_NEWS` | Company-specific news (from search/deep fetch metadata) |

#### Scenario: Category covers ingest feeds
- **WHEN** a daily calendar ingest completes
- **THEN** persisted rows use one of the four `CALENDAR_*` categories matching the source list page

### Requirement: news_items table
`nam_db` MUST provide a `news_items` SQLAlchemy model and Alembic migration.

| Column | Type | Constraints |
|--------|------|---------------|
| `id` | UUID | PK, default uuid4 |
| `source` | NewsSource | NOT NULL |
| `category` | NewsCategory | NOT NULL |
| `title` | str(512) | NOT NULL |
| `source_url` | str(2048) | NOT NULL, UNIQUE |
| `summary` | text | nullable |
| `content_markdown` | text | nullable |
| `boursorama_ticker` | str(32) | nullable |
| `published_at` | timestamptz | nullable |
| `fetched_at` | timestamptz | NOT NULL |
| `ingest_run_id` | UUID | nullable |
| `content_embedding` | vector(384) | nullable; HNSW index when not null |

The table MUST NOT include `user_id` (global per deployment in v1).

Every upsert (cron ingest or agent persist) MUST compute and store `content_embedding` from `title`, optional `summary`, and optional `content_markdown`.

#### Scenario: Upsert by source_url
- **WHEN** ingest inserts a row with an existing `source_url`
- **THEN** the existing row is updated (`title`, `summary`, `fetched_at`, `ingest_run_id`, `content_embedding` at minimum)
- **AND** existing `content_markdown` is preserved when the upsert does not supply a new body
- **AND** row count does not increase

#### Scenario: Semantic index for news search
- **WHEN** the migration is applied
- **THEN** an HNSW index exists on `content_embedding` for rows where it is not null

#### Scenario: Index for agent queries
- **WHEN** the migration is applied
- **THEN** an index exists on `(category, fetched_at DESC)` for list queries

### Requirement: IndexType enum
`nam_db.enums` MUST define `IndexType` with values `COMPANY` and `ETF`.

#### Scenario: Enum registered in PostgreSQL
- **WHEN** the Alembic migration runs
- **THEN** PostgreSQL type `indextype` exists with values `COMPANY` and `ETF`

### Requirement: indices extension columns
`indices` MUST gain `boursorama_ticker` and `index_type` columns.

| Column | Type | Constraints |
|--------|------|---------------|
| `boursorama_ticker` | str(32) | nullable |
| `index_type` | IndexType | NOT NULL, default `COMPANY` |

`boursorama_ticker` stores the Bourso internal code (e.g. `1rPAI` for equities, `1rTPUST` for trackers). `index_type` drives which tools and URLs apply — ETFs have no company news page.

#### Scenario: Migration defaults for existing rows
- **WHEN** the migration runs on a database with existing indices
- **THEN** all existing rows have `boursorama_ticker = NULL` and `index_type = COMPANY`
- **AND** portfolio and index tools continue to work

#### Scenario: User creates ETF index
- **WHEN** an index is created with `index_type=ETF` and `boursorama_ticker="1rTPUST"`
- **THEN** the row stores both values
- **AND** `SearchBoursoramaTool` returns tracker URLs (composition, not news)

#### Scenario: User-provided COMPANY ticker persisted
- **WHEN** an index is created with `index_type=COMPANY` and `boursorama_ticker="1rPAI"`
- **THEN** subsequent resolution returns company URLs without HTTP search
