## Requirements

### Requirement: AnalysisTrigger enum
The `nam-db` package MUST define `AnalysisTrigger` in `nam_db/enums.py` with PostgreSQL enum name `analysis_trigger_enum` and values: `MARKET_SESSION`, `NEWS_EVENT`, `MANUAL`, `TASK`.

#### Scenario: Enum parity
- **WHEN** `AnalysisTrigger.MARKET_SESSION` is used in code
- **THEN** its value is `"MARKET_SESSION"` matching the PostgreSQL enum type

### Requirement: Analysis ORM model
The `Analysis` model MUST map to table `analyses` with columns:

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `user_id` | UUID | FK → users.id, NOT NULL |
| `agent` | agent_enum | NOT NULL |
| `index_id` | UUID | FK → indices.id, NULL |
| `title` | VARCHAR(255) | NOT NULL |
| `content` | TEXT | NOT NULL |
| `content_embedding` | vector(384) | NOT NULL |
| `trigger` | analysis_trigger_enum | NOT NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

#### Scenario: Analysis with optional index
- **WHEN** a sector analyst report targets the CAC 40 index
- **THEN** the row may set `index_id` to that index's UUID
- **AND** macro analyses with no single instrument MAY leave `index_id` NULL

#### Scenario: Sub-agent authorship
- **WHEN** an analysis is created by a sub-agent
- **THEN** `agent` is one of `SECTOR_ANALYST`, `MACRO_STRATEGIST`, or `ETF_QUANT_SPECIALIST`
- **AND** `PORTFOLIO_MANAGER` MUST NOT appear on analyses (enforced at tool layer in a follow-up change)

### Requirement: Recommendation ORM model
The `Recommendation` model MUST map to table `recommendations` with columns:

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `user_id` | UUID | FK → users.id, NOT NULL |
| `agent` | agent_enum | NOT NULL |
| `content` | TEXT | NOT NULL |
| `type` | recommendation_type_enum | NOT NULL |
| `status` | recommendation_status_enum | NOT NULL, DEFAULT `PENDING` |
| `user_comment` | TEXT | NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| `resolved_at` | TIMESTAMPTZ | NULL |

The table MUST NOT contain `analysis_id` — links use the junction table.

#### Scenario: Default status
- **WHEN** a recommendation row is inserted without explicit status
- **THEN** `status` is `PENDING`

#### Scenario: Resolution timestamp
- **WHEN** status is updated to `APPLIED` or `REJECTED`
- **THEN** `resolved_at` is set to the current timestamp

### Requirement: Recommendation–analysis junction
Table `recommendation_analyses` MUST link recommendations to analyses many-to-many:

| Column | Type | Constraints |
|--------|------|-------------|
| `recommendation_id` | UUID | FK → recommendations.id, ON DELETE CASCADE |
| `analysis_id` | UUID | FK → analyses.id, ON DELETE RESTRICT |

Primary key: `(recommendation_id, analysis_id)`.

#### Scenario: Multiple source analyses
- **WHEN** a PM recommendation synthesizes three sub-agent reports
- **THEN** three rows exist in `recommendation_analyses` for that recommendation

#### Scenario: Duplicate link prevented
- **WHEN** the same `(recommendation_id, analysis_id)` pair is inserted twice
- **THEN** the database rejects the second insert

### Requirement: PostgreSQL enums for agent memory
The migration MUST create PostgreSQL enum types if absent: `agent_enum`, `recommendation_type_enum`, `recommendation_status_enum`, `analysis_trigger_enum`.

#### Scenario: Migration upgrade
- **WHEN** `alembic upgrade head` runs after `portfolio_core`
- **THEN** tables `analyses`, `recommendations`, and `recommendation_analyses` exist with expected FKs

### Requirement: Vector and query indexes
The migration MUST create:

- HNSW index on `analyses.content_embedding` (cosine distance)
- Btree index on `analyses(user_id, created_at DESC)`
- Btree index on `analyses(user_id, index_id)` where `index_id IS NOT NULL`
- Btree index on `recommendations(user_id, status)`

#### Scenario: User-scoped listing
- **WHEN** analyses are listed for a user ordered by date
- **THEN** the `(user_id, created_at)` index supports the query

### Requirement: Agent write boundary
Only the **agentic** module MAY INSERT into `analyses`, `recommendations`, and `recommendation_analyses`. The API MUST NOT expose create endpoints for these tables in this change.

#### Scenario: No API create routes
- **WHEN** nam-api routers are reviewed
- **THEN** no `POST /analyses` or `POST /recommendations` routes exist

### Requirement: SQLAlchemy relationships
ORM models MUST expose relationships for navigation:

- `User.analyses`, `User.recommendations`
- `Analysis.user`, optional `Analysis.index`
- `Recommendation.user`, `Recommendation.analyses` (via junction)
- `Analysis.recommendations` (back-reference via junction)

#### Scenario: Model imports
- **WHEN** `from nam_db.models import Analysis, Recommendation` is executed
- **THEN** both mapped classes inherit from `nam_db.base.Base`
