## ADDED Requirements

### Requirement: Docker Compose for PostgreSQL
The repository MUST include a `docker-compose.yml` at the root providing PostgreSQL with the pgvector extension auto-enabled via an init script.

#### Scenario: Database startup with pgvector
- **WHEN** `docker compose up -d` is run on a fresh volume
- **THEN** PostgreSQL is accessible on port 5432
- **AND** the pgvector extension is already installed (`SELECT extname FROM pg_extension WHERE extname = 'vector'` returns a row)

### Requirement: pgvector init script
A SQL init script MUST exist at `docker/postgres/init.sql` containing `CREATE EXTENSION IF NOT EXISTS vector;`, mounted via `docker-entrypoint-initdb.d` in docker-compose.

#### Scenario: No manual extension step
- **WHEN** a developer follows README setup for the first time
- **THEN** they do NOT need to run `CREATE EXTENSION vector` manually

### Requirement: Dev commands via justfile
A root `justfile` MUST provide shortcuts: `sync`, `up`, `down`, `migrate`, `api`, `worker`, `lint`.

#### Scenario: Just commands work
- **WHEN** `just --list` is run from the repo root
- **THEN** all listed commands are available

### Requirement: Environment template
A `.env.example` file MUST document all required environment variables for local development.

#### Scenario: Required variables documented
- **WHEN** a developer copies `.env.example` to `.env`
- **THEN** the file includes at minimum: `DATABASE_URL`, `LLM_MODEL`, `LLM_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `DEFAULT_USER_ID`, `MARKET_TIMEZONE`

### Requirement: Git ignore
`.gitignore` MUST exclude `.env`, `__pycache__/`, `.venv/`, `*.pyc`, and `.pytest_cache/`.

#### Scenario: Secrets not committed
- **WHEN** a developer creates a `.env` file with secrets
- **THEN** git does not track it

### Requirement: README setup instructions
The root `README.md` MUST include setup steps: install uv, `just sync`, `just up`, `just migrate`, `just api`, `just worker`.

#### Scenario: New developer onboarding
- **WHEN** a developer follows README setup steps
- **THEN** they can reach `GET /health` returning 200
- **AND** pgvector extension is confirmed active

### Requirement: Alembic run path documented
Documentation MUST specify that migrations are run from `packages/db/` using uv, with the async Alembic template.

#### Scenario: Migration command documented
- **WHEN** README is read
- **THEN** it contains the exact commands:
  - Init (one-time): `cd packages/db && alembic init -t async alembic`
  - Upgrade: `uv run --directory packages/db alembic upgrade head`
- **AND** it mentions `alembic-postgresql-enum` for PostgreSQL ENUM support
