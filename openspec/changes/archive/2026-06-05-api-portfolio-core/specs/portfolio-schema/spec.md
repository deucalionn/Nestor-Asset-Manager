## ADDED Requirements

### Requirement: Portfolio ORM models
The `nam-db` package MUST implement SQLAlchemy 2.0 async models for `users`, `indices`, `transactions`, and `positions` matching `design.md` § Models.

#### Scenario: Model imports
- **WHEN** `from nam_db.models import User, Index, Transaction, Position` is executed
- **THEN** all four mapped classes inherit from `nam_db.base.Base`

### Requirement: User date of birth
The `User` model MUST persist `date_of_birth` as `DATE NOT NULL`. It MUST NOT persist a stored `age` column.

#### Scenario: Age derived at runtime
- **WHEN** a user born 1990-01-15 is read via `UserRead`
- **THEN** `age` is computed from `date_of_birth` relative to today's date
- **AND** no `age` column exists on the `users` table

#### Scenario: Minimum age validation
- **WHEN** `UserCreate` receives a `date_of_birth` implying age under 18
- **THEN** Pydantic validation fails before persistence

### Requirement: Native PostgreSQL enums on ORM columns
Enum columns MUST use `SAEnum(..., native_enum=True, create_constraint=True)` with PostgreSQL type names from `openspec.md`.

#### Scenario: Transaction type column
- **WHEN** the `Transaction` model is inspected
- **THEN** `type` uses `TransactionType` with PostgreSQL enum name `transaction_type_enum`

### Requirement: Strategic database indexes
The migration MUST create indexes on columns used for frequent queries:

| Table | Index | Columns |
|-------|-------|---------|
| `transactions` | `ix_transactions_user_id` | `user_id` |
| `transactions` | `ix_transactions_index_id` | `index_id` |
| `transactions` | `ix_transactions_user_id_date` | `user_id`, `date` |
| `transactions` | `ix_transactions_user_id_index_id` | `user_id`, `index_id` |
| `positions` | `ix_positions_user_id` | `user_id` |
| `indices` | _(implicit)_ | `UNIQUE (isin)` |
| `positions` | _(implicit)_ | `UNIQUE (user_id, index_id)` |

#### Scenario: Migration contains indexes
- **WHEN** the `portfolio_core` Alembic revision is inspected
- **THEN** all listed transaction and position indexes are present

### Requirement: Position uniqueness
The `positions` table MUST enforce `UNIQUE (user_id, index_id)` at the database level.

#### Scenario: Duplicate position prevented
- **WHEN** two position rows share the same `user_id` and `index_id`
- **THEN** the database rejects the second insert

### Requirement: Initial Alembic migration
An Alembic revision MUST create all four portfolio tables with FKs, checks, enums, and indexes.

#### Scenario: Migration upgrade
- **WHEN** `alembic upgrade head` runs on a fresh pgvector-enabled database
- **THEN** tables `users`, `indices`, `transactions`, `positions` exist with expected indexes

### Requirement: Foreign keys
`transactions` and `positions` MUST reference `users.id` and `indices.id` with `ON DELETE RESTRICT`.

#### Scenario: Orphan transaction blocked
- **WHEN** inserting a transaction with a non-existent `index_id`
- **THEN** the database raises a foreign key violation
