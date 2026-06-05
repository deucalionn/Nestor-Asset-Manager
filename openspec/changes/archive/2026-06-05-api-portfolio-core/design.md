## Context

NAM monorepo is scaffolded. User wants agentic next but needs portfolio API first. Feedback on this change:

- **One `TransactionService`** (create / update / delete) — no `TransactionCorrectionService`
- **Keep** `PositionService` + `PositionCalculator` split
- **Tests in Docker** with pgvector (AImmo pattern: `docker-compose.test.yml` + test-runner container)

Reference: `AImmo/dev/back-end-services/main_service/docker/tests/` — Postgres service + test-runner runs migrations then pytest.

## Goals / Non-Goals

**Goals:**
- Real ORM models (see § Models below)
- Alembic migration `portfolio_core`
- Async services + thin routers
- `TransactionService` full CRUD + position recalc on every mutation
- Docker-based test suite with pgvector
- TDD workflow

**Non-Goals:**
- `analyses`, `recommendations` tables (pgvector needed in compose for future, not used in portfolio tests yet)
- Auth, WebSocket, agentic tools

## Models (planned SQLAlchemy)

All models inherit from `nam_db.base.Base`. Types use `Mapped[]` + `mapped_column`. UUIDs via `Uuid` (SQLAlchemy 2.0).

### `User` — `nam_db/models/user.py`

| Column | Python type | DB |
|--------|-------------|-----|
| `id` | `UUID` | PK, `gen_random_uuid()` |
| `firstname` | `str` | `VARCHAR(100) NOT NULL` |
| `date_of_birth` | `date` | `DATE NOT NULL` — **no stored `age`** |
| `strategy` | `Strategy` | `strategy_enum NOT NULL` |
| `goals` | `str` | `TEXT NOT NULL` |
| `created_at` | `datetime` | `TIMESTAMPTZ`, server default `now()` |
| `updated_at` | `datetime` | `TIMESTAMPTZ`, onupdate |

**Age:** computed at runtime from `date_of_birth` (Pydantic `computed_field` on `UserRead`, or helper in `nam_api/schemas/user.py`). Validation: user MUST be ≥ 18 years old at request time (Pydantic validator, not a DB column).

**DB indexes:** none beyond PK for v1 (low volume single-user).

Relationships: `transactions`, `positions` (optional `back_populates`).

### `Index` — `nam_db/models/index.py`

| Column | Python type | DB |
|--------|-------------|-----|
| `id` | `UUID` | PK |
| `name` | `str` | `VARCHAR(255) NOT NULL` |
| `isin` | `str` | `VARCHAR(12) NOT NULL UNIQUE` |
| `created_at` | `datetime` | `TIMESTAMPTZ` |

**DB indexes:** `UNIQUE (isin)` (implicit via constraint).

Relationships: `transactions`, `positions`.

### `Transaction` — `nam_db/models/transaction.py`

| Column | Python type | DB |
|--------|-------------|-----|
| `id` | `UUID` | PK |
| `user_id` | `UUID` | FK → `users.id` RESTRICT |
| `index_id` | `UUID` | FK → `indices.id` RESTRICT |
| `type` | `TransactionType` | `transaction_type_enum NOT NULL` |
| `price` | `Decimal` | `NUMERIC(18,6) NOT NULL`, check `> 0` |
| `quantity` | `Decimal` | `NUMERIC(18,8) NOT NULL`, check `> 0` |
| `date` | `datetime` | `TIMESTAMPTZ NOT NULL` (execution date) |
| `fees` | `Decimal \| None` | `NUMERIC(18,6)`, check `>= 0` |
| `created_at` | `datetime` | `TIMESTAMPTZ` (record time) |

**DB indexes (strategic):**

| Index name | Columns | Purpose |
|------------|---------|---------|
| `ix_transactions_user_id` | `user_id` | Filter ledger by user |
| `ix_transactions_index_id` | `index_id` | FK lookups |
| `ix_transactions_user_id_date` | `user_id`, `date` | List/order ledger |
| `ix_transactions_user_id_index_id` | `user_id`, `index_id` | Position recalc replay |

Defined via `__table_args__` + `Index(...)` on the model (reflected in Alembic migration).

### `Position` — `nam_db/models/position.py`

| Column | Python type | DB |
|--------|-------------|-----|
| `id` | `UUID` | PK |
| `user_id` | `UUID` | FK → `users.id` RESTRICT |
| `index_id` | `UUID` | FK → `indices.id` RESTRICT |
| `quantity` | `Decimal` | `NUMERIC(18,8) NOT NULL`, check `>= 0` |
| `average_cost` | `Decimal` | `NUMERIC(18,6) NOT NULL` |
| `last_update` | `datetime` | `TIMESTAMPTZ NOT NULL` |

**Unique:** `(user_id, index_id)` — doubles as composite index for upsert lookups.

**DB indexes:**

| Index name | Columns | Purpose |
|------------|---------|---------|
| `ix_positions_user_id` | `user_id` | `GET /users/{id}/positions` |
| `uq_positions_user_id_index_id` | `user_id`, `index_id` | UNIQUE constraint |

### Example ORM sketch

```python
# packages/db/nam_db/models/transaction.py
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nam_db.base import Base
from nam_db.enums import TransactionType


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_transactions_price_positive"),
        CheckConstraint("quantity > 0", name="ck_transactions_quantity_positive"),
        CheckConstraint("fees IS NULL OR fees >= 0", name="ck_transactions_fees_non_negative"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    index_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("indices.id"), nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType, name="transaction_type_enum", create_constraint=True, native_enum=True),
        nullable=False,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fees: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="transactions")
    index: Mapped["Index"] = relationship(back_populates="transactions")
```

_(Same style for `User`, `Index`, `Position` — full code in apply phase.)_

### ER diagram

```text
users ─────┬────< transactions >──── indices
           │
           └────< positions >──────── indices
                    UNIQUE(user_id, index_id)
```

## Decisions

### D1 — Include DB schema in this change

API TDD blocked without real tables.

### D2 — Service layering

```text
routers/indices.py       → IndexService
routers/transactions.py  → TransactionService
routers/positions.py     → PositionService (read)

services/
  index_service.py
  transaction_service.py     # create, update, delete
  position_service.py        # list + recalculate (calls calculator)
  position_calculator.py     # pure replay logic — unit tested without Docker
```

### D3 — Mutable transactions (user decision)

**Choice:** `TransactionService` supports create, update, delete. After any mutation, `PositionService.recalculate_for_user_index(user_id, index_id)` replays the full ledger for that pair.

**Rationale:** Simpler API and mental model for v1. User explicitly rejected compensating-entry service.

**Follow-up:** Update `openspec.md` §4.3.3 and ledger immutability requirement to match (mutable via API service; agents still never write).

**Alternative:** Immutable ledger + correction service — rejected per user feedback.

### D4 — Position recalculation

Replay all transactions for `(user_id, index_id)` ordered by `date`, `created_at`. Uses `PositionCalculator.replay(transactions) -> PositionSnapshot | None`.

ACB rules (openspec):
- BUY: weighted average including fees
- SELL: reduce qty, ACB unchanged; delete position if qty = 0
- Reject SELL if insufficient qty (422)

On **update** or **delete**, recalc may affect multiple indices if `index_id` changed on update — service recalculates old and new index.

### D5 — Docker test stack (AImmo pattern)

**Choice**:

```text
docker/tests/
  docker-compose.test.yml   # db (pgvector/pgvector:pg16) + test-runner
  Dockerfile.test           # uv sync, copy monorepo, run tests
.env.test                   # DATABASE_URL=...@db:5432/nam_test
justfile                    # `just test` → compose up --abort-on-container-exit
```

**test-runner CMD:** `alembic upgrade head && pytest api/tests -svv`

**conftest.py** (in container, like AImmo):
- Session-scoped: connect to Docker Postgres (pgvector enabled via init script)
- Per-test: truncate portfolio tables (or Alembic + delete all)
- `async_client` fixture with dependency override for `get_session`

**All `api/tests`** (unit, services, API): Docker only via `just test` — one command, same Postgres + Alembic as CI.

**Reference:** AImmo `main_service/conftest.py` — `setup_db`, `db_session` with table cleanup, `AsyncClient` + overrides.

### D6 — pgvector in test DB

**Choice:** Use `pgvector/pgvector:pg16` (same as dev `docker-compose.yml`) + `docker/postgres/init.sql`. Portfolio tests don't use vector columns yet, but compose matches prod and unblocks future `analyses` tests without changing infra.

### D7 — Pydantic schemas (typed input **and** output)

Every route MUST declare explicit request and response types — no raw `dict` returns.

**Pattern:**

```python
@router.post("", response_model=IndexRead, status_code=201)
async def create_index(body: IndexCreate, ...) -> IndexRead:
    ...

@router.get("", response_model=list[IndexRead])
async def list_indices(...) -> list[IndexRead]:
    ...
```

**Schemas:**

| Domain | Input | Output |
|--------|-------|--------|
| Index | `IndexCreate` | `IndexRead` |
| Transaction | `TransactionCreate`, `TransactionUpdate` | `TransactionRead` |
| Position | _(none — read-only)_ | `PositionRead` |
| User (tests/future) | `UserCreate` | `UserRead` (+ computed `age`) |

**UserRead age:**

```python
from pydantic import computed_field

class UserRead(BaseModel):
    date_of_birth: date
    # ... other fields

    @computed_field
    @property
    def age(self) -> int:
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
```

Services return Pydantic models (or ORM → `ModelRead.model_validate(orm)`), never untyped dicts.

### D8 — API routes

| Method | Route | Service method |
|--------|-------|----------------|
| GET | `/indices` | `IndexService.list` |
| POST | `/indices` | `IndexService.create` |
| GET | `/indices/{index_id}` | `IndexService.get` |
| GET | `/users/{user_id}/transactions` | `TransactionService.list_for_user` |
| POST | `/users/{user_id}/transactions` | `TransactionService.create` |
| PUT | `/users/{user_id}/transactions/{transaction_id}` | `TransactionService.update` |
| DELETE | `/users/{user_id}/transactions/{transaction_id}` | `TransactionService.delete` |
| GET | `/users/{user_id}/positions` | `PositionService.list_for_user` |

### D9 — User date of birth (not stored age)

**Choice:** Persist `date_of_birth DATE`; compute `age` in API layer only.

**Rationale:** Age changes every year — DOB is the stable fact.

**Validation:** `UserCreate` / factories reject DOB implying age &lt; 18.

### D10 — Strategic DB indexes

**Choice:** Explicit indexes on FK columns and query patterns (see § Models). Review in Alembic autogenerate — add any missing indexes manually in migration.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Mutable ledger loses audit trail vs compensating entries | Accept for v1; can add audit log later |
| Full replay on every edit | OK for v1 volume |
| Docker required for CI/local integration tests | Document `just test`; match AImmo workflow |
| openspec.md still says immutable | Update in same change during apply |

## Migration Plan

1. `alembic upgrade head` in test-runner before pytest
2. Dev: `just up && just migrate`

## Open Questions

1. **DELETE cascade:** Hard delete transaction row vs soft delete → hard delete for v1
2. **User seed:** Factory in tests only; optional `scripts/seed_dev.py` later
