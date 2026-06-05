## ADDED Requirements

### Requirement: Shared database package location
All SQLAlchemy models, enums, session factory, and Alembic migrations MUST live in `packages/db/` under the import path `nam_db`.

#### Scenario: Single model source
- **WHEN** `api/` or `agentic/` needs a database model
- **THEN** it imports from `nam_db.models` — never defines its own ORM models

### Requirement: Enum module
`nam_db/enums.py` MUST define Python enums matching PostgreSQL enums: `Strategy`, `TransactionType`, `AgentRole`, `SubAgentRole`, `RecommendationType`, `RecommendationStatus`.

#### Scenario: Enum parity
- **WHEN** `AgentRole.SECTOR_ANALYST` is used in code
- **THEN** its value is `"SECTOR_ANALYST"` matching the future `agent_enum` PostgreSQL type

### Requirement: SQLAlchemy async base
`nam_db/base.py` MUST expose a `DeclarativeBase` subclass used by all ORM models.

#### Scenario: Model inheritance
- **WHEN** a new model is added under `nam_db/models/`
- **THEN** it inherits from the shared base class

### Requirement: Centralized database settings
`nam_db/settings.py` MUST expose a `Settings` class (pydantic-settings) with `DATABASE_URL`. Both `nam_db/session.py` and `alembic/env.py` MUST import from this module — never read `os.environ` directly.

#### Scenario: Single DATABASE_URL source
- **WHEN** the API session factory and Alembic both connect to PostgreSQL
- **THEN** they use the same `DATABASE_URL` value from `nam_db.settings`

### Requirement: Async session factory
`nam_db/session.py` MUST expose an async engine and `async_sessionmaker` configured via `DATABASE_URL` environment variable.

#### Scenario: Session creation
- **WHEN** `get_session()` is called with a valid `DATABASE_URL`
- **THEN** an `AsyncSession` is returned usable for SQLAlchemy 2.0 async queries

### Requirement: Alembic async initialization
Alembic MUST be initialized using the official async template from `packages/db/`:

```bash
cd packages/db && alembic init -t async alembic
```

The generated `env.py` MUST use `async_engine_from_config` and `run_async_migrations()` — not synchronous `engine_from_config`.

#### Scenario: Async migration runtime
- **WHEN** `uv run alembic upgrade head` is executed
- **THEN** migrations run via `asyncio.run()` with an `AsyncEngine`
- **AND** `env.py` does not use a synchronous SQLAlchemy engine

### Requirement: Alembic async session alignment
Alembic `env.py` MUST share the same async database URL and engine configuration as `nam_db/session.py` (both use `postgresql+asyncpg://` via `DATABASE_URL`).

#### Scenario: URL consistency
- **WHEN** Alembic connects for autogenerate or upgrade
- **THEN** it uses the same `DATABASE_URL` as the application async session factory

### Requirement: PostgreSQL enum migrations via alembic-postgresql-enum
The `nam-db` package MUST depend on `alembic-postgresql-enum`. Alembic MUST register its autogenerate hooks so PostgreSQL native ENUM types are detected, created, altered, and dropped correctly in migrations.

#### Scenario: Enum autogenerate
- **WHEN** a model column uses `SAEnum(Strategy, name="strategy_enum", create_constraint=True, native_enum=True)`
- AND `alembic revision --autogenerate` is run
- THEN the generated migration includes proper `CREATE TYPE strategy_enum AS ENUM (...)` via alembic-postgresql-enum
- AND does not silently skip the enum type

#### Scenario: Enum package configured
- **WHEN** `packages/db/alembic/env.py` is inspected
- **THEN** it imports and calls `alembic_postgresql_enum.configure()` (or equivalent setup per package docs)

### Requirement: Alembic model discovery
Alembic `env.py` MUST import all models from `nam_db.models` so autogenerate detects the full schema.

#### Scenario: Migration command
- **WHEN** `uv run --directory packages/db alembic current` is run
- **THEN** Alembic connects using `DATABASE_URL` without import errors

### Requirement: Enum ORM mapping
SQLAlchemy enum columns MUST use `native_enum=True` with explicit PostgreSQL type names matching `nam_db/enums.py` (e.g. `SAEnum(AgentRole, name="agent_enum", create_constraint=True, native_enum=True)`).

#### Scenario: Native PostgreSQL enum
- **WHEN** an ORM model defines an enum column
- **THEN** it uses `native_enum=True` and a named PostgreSQL enum type — not a VARCHAR check constraint

### Requirement: Model module stubs
Empty model modules MUST exist for all planned entities: `user`, `index`, `transaction`, `position`, `analysis`, `recommendation`.

#### Scenario: Model package structure
- **WHEN** `from nam_db.models import user` is executed
- **THEN** the module loads without error (stub or implemented)

### Requirement: No Pydantic in nam-db
The `nam-db` package MUST NOT contain Pydantic HTTP or Tool schemas — only ORM models and enums.

#### Scenario: Separation of concerns
- **WHEN** reviewing `packages/db/` source files
- **THEN** no `BaseModel` subclasses exist outside test fixtures
