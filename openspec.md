# Nestor Asset Manager (NAM) — OpenSpec

> **Version**: 0.2.0-draft  
> **Status**: Initial design — no implementation yet  
> **Standard**: OpenSpec (Fission-AI) — master reference document  
> **Last updated**: 2026-06-01

---

## Table of contents

1. [Vision and scope](#1-vision-and-scope)
2. [Repository structure](#2-repository-structure)
3. [System architecture](#3-system-architecture)
4. [Database specifications](#4-database-specifications)
5. [API module (FastAPI)](#5-api-module-fastapi)
6. [Agentic module (Deep Agents)](#6-agentic-module-deep-agents)
7. [Autonomous market scheduler](#7-autonomous-market-scheduler)
8. [Agent design system (OOP)](#8-agent-design-system-oop)
9. [Tool catalog](#9-tool-catalog)
10. [Core business flows](#10-core-business-flows)
11. [Non-functional requirements](#11-non-functional-requirements)
12. [Out of scope and future phases](#12-out-of-scope-and-future-phases)
13. [Glossary](#13-glossary)

---

## 1. Vision and scope

### 1.1 Intent

NAM is an **autonomous** financial decision-support team. **Local Deep Agents** ([LangChain Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview) harness on LangGraph, inference via Ollama or vLLM) continuously observe markets and the portfolio, produce **textual analyses**, and **rebalancing recommendations**.

The agent runs **autonomously** on a market schedule (EU, US, Asia). **Chat is optional** — a WebSocket channel to talk to the same agent when the user wants to.

The user retains **final control**: every recommendation stays in `Pending` status until explicitly validated (`Applied` or `Rejected`) via the API.

### 1.2 Objectives

| ID | Objective | Success criterion |
|----|-----------|-------------------|
| O1 | Assisted decisions, never automated execution | No buy/sell order without user action via the API |
| O2 | Modularity and scalability | API and Agentic deployable independently, coupled via PostgreSQL |
| O3 | Long-term semantic memory | pgvector search over analysis history and user feedback |
| O4 | Financial traceability | Immutable ledger (Transaction) + position snapshot (Position) |
| O5 | Runtime personalization | User context (strategy, goals) injected into agent runtime |
| O6 | Autonomous market observation | Agent runs scheduled briefs/checks without user interaction |
| O7 | Clean, modular codebase | OOP-first design — classes, not dict configs |

### 1.3 Scope (included)

- **Monorepo** with shared `packages/db` (SQLAlchemy models + Alembic)
- **API module** — async FastAPI: auth, financial CRUD, WebSocket chat, recommendation management
- **Agentic module** — Deep Agents harness: PM + subagents, custom tools, market scheduler worker
- **PostgreSQL + pgvector**: structured data + embeddings
- **Frontend** (API consumer): functional scope defined, implementation deferred
- Pydantic v2 schemas for all Tool and API interfaces
- OOP architecture throughout the Python codebase

### 1.4 Non-goals (excluded from v1)

- Order execution on real brokers (IBKR, Binance, etc.)
- Direct agent writes to `Transaction` or `Position`
- Enterprise OAuth / SSO (simple auth in v1)
- Multi-tenant / concurrent multi-user (one active user per agent session in v1)
- Automated quantitative backtesting
- Managed cloud deployment (local/on-prem infra in v1)
- Hand-built LangGraph routing graphs (use Deep Agents harness instead)

### 1.5 Actors

| Actor | Role |
|-------|------|
| **User (human PM)** | Validates or rejects recommendations, records transactions, optionally chats with the agent |
| **Portfolio Manager (Deep Agent)** | Main agent — orchestrates subagents via `task()`, creates recommendations |
| **Sector Analyst (subagent)** | Analyzes individual equities |
| **Macro Strategist (subagent)** | Analyzes macroeconomic and geopolitical context |
| **ETF & Quant Specialist (subagent)** | Analyzes indices and passive instruments |
| **Market Scheduler (worker)** | Triggers the Deep Agent at market session times |
| **API Module** | HTTP/WS entry point, persistence, access control |
| **PostgreSQL** | Data bus, structured and vector memory |

### 1.6 Code conventions

| Rule | Detail |
|------|--------|
| **Language** | All code identifiers in English (columns, classes, modules, routes, tools) |
| **Specs language** | English |
| **Conversation** | French (team communication) |
| **Paradigm** | OOP-first — agents, tools, and schedulers are **classes**; system prompts are **markdown files** |
| **No dict configs** | Subagent definitions MUST NOT be raw dicts passed to `create_deep_agent`; use class-based specs with a `to_spec()` method |
| **Enums everywhere** | Domain values MUST use Python `Enum` classes from `nam_db.enums` — never `Literal[...]` string unions |
| **DB/Python parity** | Every PostgreSQL enum MUST have a matching Python enum with identical member values |
| **Separation** | SQLAlchemy models ≠ Pydantic schemas; ORM in `packages/db`, HTTP schemas in `api/`, Tool schemas in `agentic/` |

---

## 2. Repository structure

### 2.1 Monorepo layout

```text
nam/
├── pyproject.toml                 # uv/poetry workspace root
├── openspec.md
├── openspec/
│
├── packages/
│   └── db/                        # Shared package: nam-db
│       ├── pyproject.toml
│       ├── alembic/
│       │   ├── env.py
│       │   └── versions/
│       └── nam_db/
│           ├── base.py            # DeclarativeBase
│           ├── session.py         # async engine + session factory
│           ├── enums.py
│           └── models/
│               ├── user.py
│               ├── index.py
│               ├── transaction.py
│               ├── position.py
│               ├── analysis.py
│               └── recommendation.py
│
├── api/
│   ├── pyproject.toml             # depends: nam-db, nam-agentic (chat)
│   └── nam_api/
│       ├── main.py
│       ├── routers/
│       ├── services/              # business logic (position recalc, reco feedback)
│       ├── schemas/               # Pydantic HTTP request/response
│       └── websocket/
│           └── chat.py            # in-process Deep Agent streaming
│
└── agentic/
    ├── pyproject.toml             # depends: nam-db
    └── nam_agentic/
        ├── factory.py             # DeepAgentFactory — builds the compiled graph
        ├── runner.py              # AgentRunner — invoke/stream wrapper
        ├── agents/                # OOP agent definitions
        │   ├── base.py
        │   ├── portfolio_manager.py
        │   ├── sector_analyst.py
        │   ├── macro_strategist.py
        │   └── etf_quant.py
        ├── prompts/               # Markdown system prompts (one .md per agent)
        │   ├── loader.py          # PromptLoader — reads {NAME}.md
        │   ├── PORTFOLIO.md
        │   ├── SECTOR_ANALYST.md
        │   ├── MACRO_STRATEGIST.md
        │   └── ETF_QUANT.md
        ├── tools/                 # Tool classes (one file per tool)
        │   ├── base.py
        │   ├── portfolio/
        │   └── market/
        ├── scheduler/
        │   ├── markets.py         # MarketSession definitions (EU/US/ASIA)
        │   └── worker.py          # APScheduler → AgentRunner
        ├── context.py             # NamRuntimeContext dataclass
        └── enums.py               # Market, MarketPhase (runtime-only)
```

### 2.2 Package dependencies

```text
packages/db  ◄───  api
     ▲
     └──────────  agentic  ◄───  api (chat only — in-process import)
```

| Package | Depends on | Provides |
|---------|------------|----------|
| `nam-db` | — | SQLAlchemy models, Alembic migrations, async session |
| `nam-agentic` | `nam-db` | Deep Agent factory, tools, scheduler worker |
| `nam-api` | `nam-db`, `nam-agentic` | REST + WebSocket, business services |

### 2.3 Shared database rules

- **One Alembic history** in `packages/db/alembic/` — run migrations once before starting any process
- **Alembic async template** — initialized with `alembic init -t async alembic` from `packages/db/`; migrations run via `AsyncEngine`, never sync
- **PostgreSQL enum migrations** — use `alembic-postgresql-enum` so native ENUM types are tracked in autogenerate and revision files
- **Both modules import `nam_db`** — never duplicate models
- **Write boundaries enforced in services/tools**, not in the ORM layer

**Alembic setup** (from `packages/db/`):
```bash
alembic init -t async alembic
```

**Enum migration support** (`packages/db/alembic/env.py`):
```python
from alembic_postgresql_enum import configure
configure()
```

### 2.4 Runtime processes

```bash
# Process 1 — API (REST + WebSocket chat)
uvicorn nam_api.main:app

# Process 2 — Autonomous scheduler (runs 24/7)
python -m nam_agentic.scheduler.worker
```

---

## 3. System architecture

### 3.1 Overview

```text
                         AUTONOMOUS (primary)
                         ════════════════════
┌──────────────┐    invoke     ┌──────────────────┐
│  Scheduler   │──────────────►│   Deep Agent     │
│  (worker)    │               │  PM + subagents  │
└──────────────┘               └────────┬─────────┘
                                        │
                              tools + writes
                                        ▼
┌─────────────┐   REST/WS    ┌──────────────────┐     ┌──────────────────┐
│  Frontend   │◄───────────►│   API Module     │────►│  Deep Agent      │
│             │              │   (FastAPI)      │chat │  (in-process)    │
└─────────────┘              └────────┬─────────┘     └──────────────────┘
                                      │
                            SQLAlchemy │ async
                                      ▼
                        ┌─────────────────────────────┐
                        │   PostgreSQL + pgvector      │
                        │   Financial │ Analyses │ Vec │
                        └─────────────────────────────┘
                                      ▲
                                      │
                            SQLAlchemy │ async (read + limited write)
                                      │
                              ┌───────┴────────┐
                              │  Agentic tools │
                              └────────────────┘
```

### 3.2 Architectural principles

| Principle | Description | Consequence |
|-----------|-------------|-------------|
| **Autonomous first** | Agent observes markets on schedule without user action | Scheduler worker is a core process, not an optional add-on |
| **Shared DB, shared models** | Single PostgreSQL + single `nam-db` package | One Alembic, one source of schema truth |
| **Agent read/write separation** | Agents write only `Analysis` and `Recommendation` | `Transaction`/`Position` reserved for API services |
| **Ledger immutability** | `Transaction` is append-only | Corrections via compensating transactions |
| **Human-in-the-loop via API** | `Pending → Applied/Rejected` only through API | Agents always create recommendations as `Pending` |
| **Deep Agents harness** | Use `create_deep_agent` + subagents, not hand-built graphs | PM delegates via built-in `task()` tool |
| **Chat is optional** | Same Deep Agent, different trigger | API imports `nam-agentic` in-process for WebSocket streaming |
| **OOP modularity** | Agents and tools as classes; prompts as markdown | Testable code, editable prompts without redeploy |

### 3.3 Table access matrix

| Table | API Module | Agentic Module |
|-------|:----------:|:--------------:|
| `users` | R/W | R |
| `indices` | R/W | R |
| `transactions` | R/W (append) | **—** |
| `positions` | R/W (snapshot) | R |
| `analyses` | R | R/W |
| `recommendations` | R/W (status, comment) | R/W (create Pending) |

### 3.4 Communication patterns

| Pattern | Trigger | Execution | Use case |
|---------|---------|-------------|----------|
| **Scheduled** | APScheduler at market times | Worker → `AgentRunner.invoke()` | Autonomous market briefs/checks |
| **Chat** | User WebSocket message | API → `AgentRunner.stream()` in-process | Optional conversation |
| **Manual** | `POST /users/{id}/trigger-analysis` | Worker or in-process (v1: in-process OK) | On-demand full analysis |

**Data flow (autonomous cycle)**:
1. Scheduler fires at market time (e.g. EU pre-open −10 min)
2. `AgentRunner` invokes Deep Agent with `NamRuntimeContext(market=Market.EU, phase=MarketPhase.PRE_OPEN)`
3. PM calls `write_todos`, delegates to subagents via `task()`, synthesizes
4. Subagents call `create_analysis` → PostgreSQL + pgvector
5. PM calls `create_recommendation` → status `Pending`
6. Frontend polls API for new recommendations

### 3.5 Technology stack

| Layer | Technology | Target version |
|-------|------------|----------------|
| API | FastAPI | ≥ 0.110 |
| ORM | SQLAlchemy | 2.0 (async) |
| Validation | Pydantic | v2 |
| Migrations | Alembic (async template) + alembic-postgresql-enum | latest |
| Agent harness | `deepagents` (LangChain Deep Agents) | latest stable |
| Runtime | LangGraph (via Deep Agents) | latest stable |
| Scheduler | APScheduler | ≥ 3.10 |
| Local LLM | Ollama / vLLM | configurable |
| Embeddings | local model (e.g. nomic-embed, bge) | 384 or 1024 dims |
| Database | PostgreSQL | ≥ 15 |
| Vector | pgvector | ≥ 0.7 |
| Monorepo | uv workspace (recommended) or poetry | latest |

### 3.6 Memory model — two layers

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Working memory** | Deep Agents virtual filesystem + context compression | Session context, tool output offloading, conversation threads |
| **Domain memory** | PostgreSQL + pgvector | Persistent analyses, recommendations, portfolio, semantic search via `search_past_analyses` |

Do not replace pgvector with LangGraph Store for domain analyses — both coexist.

---

## 4. Database specifications

### 4.1 Entity-relationship diagram

```text
User ─────────────┬──────────── Transaction ──────── Index
  │               │                    │
  │               └──────── Position ──┘
  │
  ├── Analysis (content_embedding: vector)
  │
  └── Recommendation ──── (FK) ──── Analysis
```

### 4.2 PostgreSQL enums

```sql
CREATE TYPE strategy_enum AS ENUM (
  'CONSERVATIVE',
  'BALANCED',
  'GROWTH',
  'AGGRESSIVE'
);

CREATE TYPE transaction_type_enum AS ENUM ('BUY', 'SELL');

CREATE TYPE agent_enum AS ENUM (
  'PORTFOLIO_MANAGER',
  'SECTOR_ANALYST',
  'MACRO_STRATEGIST',
  'ETF_QUANT_SPECIALIST'
);

CREATE TYPE recommendation_type_enum AS ENUM ('BUY', 'HOLD', 'SELL');

CREATE TYPE recommendation_status_enum AS ENUM (
  'PENDING',
  'APPLIED',
  'REJECTED'
);
```

### 4.2.1 Shared Python enums (`nam_db/enums.py`)

Every PostgreSQL enum above has a **1:1 Python counterpart** in `packages/db/nam_db/enums.py`.  
This module is the **single source of truth** for domain values across SQLAlchemy models, Pydantic schemas, and tools.

**Rules**:
- Enum member **names** and **values** MUST match PostgreSQL exactly (UPPER_SNAKE_CASE)
- NEVER use `Literal["BUY", "SELL"]` or raw strings for domain values
- API and Agentic packages import enums from `nam_db.enums` — do not redefine them
- SQLAlchemy columns use `SAEnum(EnumClass, name="postgres_enum_name", create_constraint=True, native_enum=True)`
- Alembic autogenerate for enums requires `alembic-postgresql-enum` configured in `env.py`

```python
# packages/db/nam_db/enums.py
from enum import Enum


class Strategy(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    BALANCED = "BALANCED"
    GROWTH = "GROWTH"
    AGGRESSIVE = "AGGRESSIVE"


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class AgentRole(str, Enum):
    PORTFOLIO_MANAGER = "PORTFOLIO_MANAGER"
    SECTOR_ANALYST = "SECTOR_ANALYST"
    MACRO_STRATEGIST = "MACRO_STRATEGIST"
    ETF_QUANT_SPECIALIST = "ETF_QUANT_SPECIALIST"


class SubAgentRole(str, Enum):
    """Roles allowed to author analyses (subset of AgentRole — excludes PM)."""
    SECTOR_ANALYST = "SECTOR_ANALYST"
    MACRO_STRATEGIST = "MACRO_STRATEGIST"
    ETF_QUANT_SPECIALIST = "ETF_QUANT_SPECIALIST"


class RecommendationType(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


class RecommendationStatus(str, Enum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
```

**SQLAlchemy model usage**:

```python
from sqlalchemy import Enum as SAEnum
from nam_db.enums import AgentRole, RecommendationStatus, Strategy


class Analysis(Base):
    agent: Mapped[AgentRole] = mapped_column(
        SAEnum(AgentRole, name="agent_enum", create_constraint=True, native_enum=True),
        nullable=False,
    )
```

### 4.2.2 Alembic async migrations

Alembic MUST be initialized with the **async template** and aligned with the application's async session factory.

**Initialization** (run once from `packages/db/`):
```bash
cd packages/db && alembic init -t async alembic
```

**Requirements**:
- `env.py` uses `async_engine_from_config` and `run_async_migrations()` via `asyncio.run()`
- `DATABASE_URL` uses the `postgresql+asyncpg://` driver — same URL as `nam_db/session.py`
- Do NOT use the default sync Alembic template

**Dependencies** (`packages/db/pyproject.toml`):
- `alembic`
- `alembic-postgresql-enum`
- `asyncpg`

**`env.py` enum hook**:
```python
from alembic_postgresql_enum import configure

configure()  # enables PostgreSQL ENUM autogenerate support
```

**Commands**:
```bash
# from packages/db/
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
uv run alembic current
```

**Enum mapping table**:

| PostgreSQL enum | Python enum | Used in |
|-----------------|-------------|---------|
| `strategy_enum` | `Strategy` | `users.strategy` |
| `transaction_type_enum` | `TransactionType` | `transactions.type` |
| `agent_enum` | `AgentRole` | `analyses.agent`, `recommendations.agent` |
| — | `SubAgentRole` | `CreateAnalysisTool` input (subset of `AgentRole`) |
| `recommendation_type_enum` | `RecommendationType` | `recommendations.type` |
| `recommendation_status_enum` | `RecommendationStatus` | `recommendations.status` |

**Runtime-only enums** (not persisted in DB — live in `nam_agentic/enums.py`):

```python
class Market(str, Enum):
    EU = "EU"
    US = "US"
    ASIA = "ASIA"


class MarketPhase(str, Enum):
    PRE_OPEN = "PRE_OPEN"
    POST_OPEN = "POST_OPEN"
    PERIODIC = "PERIODIC"
    CLOSE = "CLOSE"
    CHAT = "CHAT"
    MANUAL = "MANUAL"
```

### 4.3 Tables

#### 4.3.1 `users`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Identifier |
| `firstname` | VARCHAR(100) | NOT NULL | First name |
| `age` | INTEGER | NOT NULL, CHECK (age >= 18) | Age |
| `strategy` | strategy_enum | NOT NULL | Risk profile |
| `goals` | TEXT | NOT NULL | Financial goals (free text) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

#### 4.3.2 `indices`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `name` | VARCHAR(255) | NOT NULL | Display name (e.g. "CAC 40") |
| `isin` | VARCHAR(12) | NOT NULL, UNIQUE | ISIN code |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

#### 4.3.3 `transactions` (Ledger — immutable)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `user_id` | UUID | FK → users.id, NOT NULL | |
| `index_id` | UUID | FK → indices.id, NOT NULL | |
| `type` | transaction_type_enum | NOT NULL | BUY or SELL |
| `price` | NUMERIC(18,6) | NOT NULL, CHECK (price > 0) | Unit price |
| `quantity` | NUMERIC(18,8) | NOT NULL, CHECK (quantity > 0) | Quantity |
| `date` | TIMESTAMPTZ | NOT NULL | Execution date |
| `fees` | NUMERIC(18,6) | NULL, CHECK (fees >= 0) | Optional fees |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Record timestamp |

**Rule**: no UPDATE/DELETE — corrections via compensating transaction.

#### 4.3.4 `positions` (Snapshot)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `user_id` | UUID | FK → users.id, NOT NULL | |
| `index_id` | UUID | FK → indices.id, NOT NULL | |
| `quantity` | NUMERIC(18,8) | NOT NULL, CHECK (quantity >= 0) | Held quantity |
| `average_cost` | NUMERIC(18,6) | NOT NULL | Average cost basis (ACB) |
| `last_update` | TIMESTAMPTZ | NOT NULL | Last snapshot update |

**Constraint**: UNIQUE `(user_id, index_id)`

**Recalculation rules (API only)**:
- BUY: new ACB = (old_qty × old_acb + qty × price + fees) / (old_qty + qty)
- SELL: qty decreases, ACB unchanged; if qty = 0, delete the position

#### 4.3.5 `analyses`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `user_id` | UUID | FK → users.id, NOT NULL | |
| `agent` | agent_enum | NOT NULL | Author agent |
| `content` | TEXT | NOT NULL | Textual report |
| `content_embedding` | vector(N) | NOT NULL | Semantic embedding (N=384 or 1024) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

#### 4.3.6 `recommendations`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `user_id` | UUID | FK → users.id, NOT NULL | |
| `analysis_id` | UUID | FK → analyses.id, NOT NULL | Source analysis |
| `agent` | agent_enum | NOT NULL | Proposing agent |
| `content` | TEXT | NOT NULL | Recommendation rationale |
| `type` | recommendation_type_enum | NOT NULL | BUY / HOLD / SELL |
| `status` | recommendation_status_enum | NOT NULL, DEFAULT 'PENDING' | |
| `user_comment` | TEXT | NULL | User comment |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `resolved_at` | TIMESTAMPTZ | NULL | Applied/Rejected date |

### 4.4 Database requirements (OpenSpec)

#### Requirement: Enum parity
Every PostgreSQL enum MUST have a matching Python `Enum` in `nam_db/enums.py` with identical values. Domain fields MUST NOT use `Literal[...]` or raw strings.

##### Scenario: Creating an analysis
- GIVEN a subagent completes a report
- WHEN `CreateAnalysisTool` is called with `agent=SubAgentRole.SECTOR_ANALYST`
- THEN the value persisted in `analyses.agent` is `AgentRole.SECTOR_ANALYST`
- AND the Python type is `AgentRole`, not a plain string

#### Requirement: Ledger immutability
The system MUST forbid modification or deletion of a `transactions` row.

##### Scenario: Correction attempt
- GIVEN a recorded transaction with an incorrect price
- WHEN the API receives a correction request
- THEN a new compensating transaction is created
- AND the original transaction remains unchanged

#### Requirement: Analysis vectorization
Every `Analysis` created by the Agentic module MUST include a `content_embedding` computed before persistence.

##### Scenario: Analysis creation
- GIVEN an agent that has written a textual report
- WHEN the `CreateAnalysisTool` is invoked
- THEN the content is embedded via the configured model
- AND the row is inserted with embedding and timestamp

#### Requirement: Semantic search
The system MUST support cosine similarity search on `analyses.content_embedding` filtered by `user_id`.

##### Scenario: Historical search
- GIVEN a user with 50 past analyses
- WHEN an agent calls `SearchPastAnalysesTool` with a query
- THEN the top-K most similar analyses are returned
- AND only analyses belonging to that user are included

---

## 5. API module (FastAPI)

### 5.1 Responsibilities

- Authentication and authorization
- Async REST endpoints for the Frontend
- WebSocket chat — in-process `AgentRunner.stream()` (optional user channel)
- CRUD for `User`, `Index`, `Transaction`, `Position`
- Read `Analysis`, manage `Recommendation` (user feedback)
- Recalculate `Position` snapshot after each transaction
- On-demand analysis trigger (`POST /users/{id}/trigger-analysis`)

### 5.2 Planned endpoints (v1)

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | Healthcheck |
| GET/PUT | `/users/{id}` | User profile |
| GET/POST | `/indices` | Index catalog |
| GET/POST | `/users/{id}/transactions` | Ledger |
| GET | `/users/{id}/positions` | Portfolio snapshot |
| GET | `/users/{id}/analyses` | Analysis list |
| GET | `/users/{id}/recommendations` | Recommendation list |
| PATCH | `/recommendations/{id}` | Applied/Rejected + comment |
| POST | `/users/{id}/trigger-analysis` | On-demand analysis |
| WS | `/ws/chat/{user_id}` | Optional chat with Deep Agent |

### 5.3 API Pydantic schemas (excerpts)

```python
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from nam_db.enums import (
    RecommendationStatus,
    Strategy,
    TransactionType,
)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    firstname: str
    age: int = Field(ge=18)
    strategy: Strategy
    goals: str


class TransactionCreate(BaseModel):
    index_id: UUID
    type: TransactionType
    price: Decimal = Field(gt=0)
    quantity: Decimal = Field(gt=0)
    date: datetime
    fees: Decimal | None = Field(default=None, ge=0)


class RecommendationFeedback(BaseModel):
    status: RecommendationStatus  # APPLIED or REJECTED only — validate in service layer
    user_comment: str | None = None
```

---

## 6. Agentic module (Deep Agents)

### 6.1 What is Deep Agents?

Deep Agents is LangChain's **agent harness** built on LangGraph. Instead of hand-wiring a `StateGraph`, NAM uses `create_deep_agent()` which provides:

| Built-in capability | Tool / feature | NAM usage |
|--------------------|----------------|-----------|
| Planning | `write_todos` | PM decomposes market briefs |
| Subagent delegation | `task` | PM → Sector / Macro / ETF analysts |
| Context management | Virtual filesystem + compression | Long analysis sessions |
| Custom tools | User-defined | Portfolio, market, DB tools |
| Streaming | LangGraph `.stream()` | WebSocket chat |
| Runtime context | Per-invoke context propagation | `market`, `phase`, `user_id` |

Reference: [Deep Agents overview](https://docs.langchain.com/oss/python/deepagents/overview)

### 6.2 Responsibilities

- Build and run the Deep Agent graph via `DeepAgentFactory`
- Execute autonomous market observation cycles (scheduler worker)
- Serve chat requests via `AgentRunner` (imported by API)
- Invoke custom Tool classes (portfolio, market data, DB writes)
- Produce vectorized `Analysis` records and `Recommendation` records (`Pending`)
- **Prohibited**: writes to `Transaction`/`Position`, order execution

### 6.3 Execution model

```text
                    create_deep_agent()
                           │
              ┌────────────┴────────────┐
              │   Portfolio Manager     │  ← main Deep Agent
              │   tools: portfolio_*    │
              │   write_todos, task()   │
              └────────────┬────────────┘
                           │ task("sector-analyst", ...)
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        SectorAnalyst  MacroStrategist  EtfQuant
        (subagent)     (subagent)       (subagent)
              │            │            │
              └────────────┴────────────┘
                           │ results only (isolated context)
                           ▼
              PM synthesizes → create_recommendation (Pending)
```

The PM orchestrates via Deep Agents' built-in `task()` tool. **No manual LangGraph node/edge wiring.**

### 6.4 Runtime context

```python
from dataclasses import dataclass
from uuid import UUID

from nam_agentic.enums import Market, MarketPhase


@dataclass(frozen=True)
class NamRuntimeContext:
    user_id: UUID
    market: Market | None = None
    phase: MarketPhase | None = None
    thread_id: str | None = None
```

Passed to `agent.invoke(..., context=runtime_context)`. Propagates automatically to all subagents and tools.

---

## 7. Autonomous market scheduler

### 7.1 Intent

The agent is **primarily autonomous**. It observes EU, US, and Asian markets on a fixed rhythm without user interaction.

### 7.2 Check rhythm (per market)

For each market session (EU, US, ASIA):

| Phase | Timing | Purpose |
|-------|--------|---------|
| `MarketPhase.PRE_OPEN` | **10 min before** market open | Pre-open brief — overnight news, expected movers |
| `MarketPhase.POST_OPEN` | **20 min after** market open | Post-open check — opening reaction, volume, gaps |
| `MarketPhase.PERIODIC` | **Every 2 hours** until close | Mid-session monitoring |
| `MarketPhase.CLOSE` | **At market close** | Closing brief — session summary |

### 7.3 Default market hours (Europe/Paris timezone)

| Market | Open | Close | Notes |
|--------|------|-------|-------|
| **EU** | 09:00 | 17:30 | Euronext / CAC / DAX |
| **US** | 15:30 | 22:00 | NYSE/NASDAQ (9:30–16:00 ET) |
| **ASIA** | 02:00 | 08:00 | Tokyo/HK overnight window (TBD — refine in implementation) |

> Asia hours are approximate and MUST be refined during implementation based on target indices.

### 7.4 Example daily schedule (EU)

```text
08:50  PRE_OPEN
09:20  POST_OPEN
11:20  PERIODIC
13:20  PERIODIC
15:20  PERIODIC
17:30  CLOSE
```

### 7.5 Scheduler architecture

```text
MarketScheduler
      │
      │ reads MarketSession configs
      │ computes cron triggers from open/close times
      ▼
APScheduler (AsyncIOScheduler)
      │
      │ at each trigger
      ▼
AgentRunner.invoke(
    message="Run pre-open brief for EU markets.",
    context=NamRuntimeContext(user_id=..., market=Market.EU, phase=MarketPhase.PRE_OPEN),
)
```

### 7.6 Requirement: Autonomous observation

The system MUST run market observation cycles without user interaction at the configured schedule.

##### Scenario: EU pre-open brief
- GIVEN the scheduler worker is running
- AND the current time is 08:50 Europe/Paris on a weekday
- WHEN the EU pre-open trigger fires
- THEN the Deep Agent is invoked with `market=Market.EU, phase=MarketPhase.PRE_OPEN`
- AND at least one `Analysis` is persisted to PostgreSQL

---

## 8. Agent design system (OOP)

### 8.1 Design principles

All agentic code MUST follow OOP patterns:

- **One class per agent** — no inline dict configs
- **One class per tool** — implements `BaseNamTool`
- **One markdown file per prompt** — `{NAME}.md` loaded via `PromptLoader`
- **Factory pattern** — `DeepAgentFactory` assembles the graph
- **Dependency injection** — tools receive session/repos via constructor

### 8.2 Class hierarchy

```text
BaseSubAgent (ABC)
├── SectorAnalystAgent
├── MacroStrategistAgent
└── EtfQuantSpecialistAgent

PortfolioManagerAgent          ← wraps main agent config (not a subagent)

BaseNamTool (ABC)
├── GetUserContextTool
├── GetPortfolioPositionsTool
├── CalculatePortfolioWeightsTool
├── CreateRecommendationTool
├── CreateIndexTool
├── CreateAnalysisTool
├── SearchPastAnalysesTool
├── GetMarketPriceTool
├── GetFinancialsNewsTool
├── GetDataFromUrlTool
└── GetCompanyFinancialsTool

PromptLoader                   ← loads {NAME}.md from prompts/
PORTFOLIO.md                   ← PM system prompt
SECTOR_ANALYST.md              ← subagent system prompt
MACRO_STRATEGIST.md
ETF_QUANT.md

DeepAgentFactory               ← builds compiled graph
AgentRunner                    ← invoke/stream wrapper
MarketScheduler                ← APScheduler registration
MarketSession                  ← dataclass for market hours
```

### 8.3 Base subagent

```python
from abc import ABC, abstractmethod
from langchain_core.tools import BaseTool


class BaseSubAgent(ABC):
    """Base class for all NAM subagents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier used by the PM's task() tool."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Action-oriented description — PM uses this to decide delegation."""

    @property
    @abstractmethod
    def prompt_file(self) -> str:
        """Markdown prompt filename without extension (e.g. SECTOR_ANALYST)."""

    @abstractmethod
    def tools(self) -> list[BaseTool]:
        """Return LangChain tools available to this subagent."""

    def system_prompt(self) -> str:
        return self._prompt_loader.load(self.prompt_file)

    def to_spec(self) -> dict:
        """Convert to Deep Agents subagent spec."""
        return {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt(),
            "tools": self.tools(),
        }
```

### 8.4 Sector analyst implementation

```python
class SectorAnalystAgent(BaseSubAgent):

    def __init__(self, tool_registry: "ToolRegistry") -> None:
        self._tools = tool_registry

    @property
    def name(self) -> str:
        return "sector-analyst"

    @property
    def description(self) -> str:
        return "Analyzes individual equities, sectors, and company fundamentals."

    @property
    def prompt_file(self) -> str:
        return "SECTOR_ANALYST"

    def tools(self) -> list[BaseTool]:
        return [
            self._tools.get_company_financials,
            self._tools.get_financials_news,
            self._tools.get_data_from_url,
            self._tools.get_market_price,
            self._tools.create_analysis,
            self._tools.search_past_analyses,
        ]
```

### 8.5 Portfolio manager

```python
class PortfolioManagerAgent:
    """Configuration for the main Deep Agent (orchestrator)."""

    def __init__(
        self,
        tool_registry: "ToolRegistry",
        prompt_loader: "PromptLoader | None" = None,
    ) -> None:
        self._tools = tool_registry
        self._prompt_loader = prompt_loader or PromptLoader()

    PROMPT_FILE = "PORTFOLIO"

    def tools(self) -> list[BaseTool]:
        return [
            self._tools.get_user_context,
            self._tools.get_portfolio_positions,
            self._tools.calculate_portfolio_weights,
            self._tools.create_recommendation,
            self._tools.create_index,
        ]

    def system_prompt(self) -> str:
        return self._prompt_loader.load(self.PROMPT_FILE)
```

### 8.6 Deep agent factory

```python
from deepagents import create_deep_agent


class DeepAgentFactory:
    """Assembles and returns the compiled NAM Deep Agent graph."""

    def __init__(
        self,
        model: str,
        portfolio_manager: PortfolioManagerAgent,
        subagents: list[BaseSubAgent],
    ) -> None:
        self._model = model
        self._pm = portfolio_manager
        self._subagents = subagents

    def build(self):
        return create_deep_agent(
            model=self._model,
            system_prompt=self._pm.system_prompt(),
            tools=self._pm.tools(),
            subagents=[agent.to_spec() for agent in self._subagents],
        )
```

### 8.7 Tool registry

```python
class ToolRegistry:
    """Central registry — injects DB session / repos into all tool classes."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory
        self._init_tools()

    def _init_tools(self) -> None:
        self.get_user_context = GetUserContextTool(self._session_factory).as_tool()
        self.get_portfolio_positions = GetPortfolioPositionsTool(self._session_factory).as_tool()
        self.create_analysis = CreateAnalysisTool(self._session_factory).as_tool()
        # ... etc.
```

### 8.8 Base tool pattern

```python
class BaseNamTool(ABC):
    """Base class for NAM custom tools."""

    @abstractmethod
    def as_tool(self) -> BaseTool:
        """Return the LangChain tool callable bound to this instance."""
```

```python
class CreateAnalysisTool(BaseNamTool):
    """Persists an analysis with pgvector embedding."""

    def __init__(self, session_factory: async_sessionmaker, embedder: EmbeddingService) -> None:
        self._session_factory = session_factory
        self._embedder = embedder

    def as_tool(self) -> BaseTool:
        @tool(args_schema=CreateAnalysisInput)
        async def create_analysis(input: CreateAnalysisInput) -> CreateAnalysisOutput:
            ...
        return create_analysis
```

### 8.9 Agent runner

```python
class AgentRunner:
    """Thin wrapper around the compiled Deep Agent graph."""

    def __init__(self, factory: DeepAgentFactory) -> None:
        self._agent = factory.build()

    async def invoke(self, message: str, context: NamRuntimeContext) -> dict:
        return await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            context=context,
        )

    async def stream(self, message: str, context: NamRuntimeContext):
        async for chunk in self._agent.astream(
            {"messages": [{"role": "user", "content": message}]},
            context=context,
        ):
            yield chunk
```

### 8.10 Agent roles summary

| Class | Deep Agents role | Tools |
|-------|------------------|-------|
| `PortfolioManagerAgent` | Main agent | `get_user_context`, `get_portfolio_positions`, `calculate_portfolio_weights`, `create_recommendation`, `create_index` |
| `SectorAnalystAgent` | Subagent | `get_company_financials`, `get_financials_news`, `get_data_from_url`, `get_market_price`, `create_analysis`, `search_past_analyses` |
| `MacroStrategistAgent` | Subagent | `get_financials_news`, `get_data_from_url`, `get_market_price`, `create_analysis`, `search_past_analyses` |
| `EtfQuantSpecialistAgent` | Subagent | `get_financials_news`, `get_data_from_url`, `get_market_price`, `create_analysis`, `search_past_analyses` |

### 8.11 PM behavior (via system prompt)

`PORTFOLIO.md` MUST include instructions covering:

1. Always call `get_user_context` and `get_portfolio_positions` first
2. Use `write_todos` to plan the cycle
3. Delegate to subagents via `task()` — parallel when possible
4. Weight subagent outputs according to user strategy
5. Call `search_past_analyses` before final synthesis
6. Create exactly one recommendation via `create_recommendation` (status `Pending`)
7. Never place orders — human validates via API

Subagent markdown prompts (`SECTOR_ANALYST.md`, etc.) MUST NOT include direct recommendation instructions.

---

## 9. Tool catalog

> All tools are **classes** implementing `BaseNamTool`.  
> Input/output validated via **Pydantic v2** schemas.

### 9.1 Portfolio Manager tools

#### `GetUserContextTool`

```python
from nam_db.enums import Strategy


class GetUserContextInput(BaseModel):
    user_id: UUID


class UserContextOutput(BaseModel):
    user_id: UUID
    firstname: str
    age: int
    strategy: Strategy
    goals: str
```

| Field | Description |
|-------|-------------|
| **DB access** | SELECT `users` |
| **Errors** | `UserNotFoundError` if missing |

---

#### `GetPortfolioPositionsTool`

```python
class PositionItem(BaseModel):
    index_id: UUID
    index_name: str
    isin: str
    quantity: Decimal
    average_cost: Decimal
    last_update: datetime
    current_price: Decimal | None = None
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None


class GetPortfolioPositionsOutput(BaseModel):
    user_id: UUID
    positions: list[PositionItem]
    total_market_value: Decimal | None = None
```

| Field | Description |
|-------|-------------|
| **DB access** | SELECT `positions` JOIN `indices` |

---

#### `CalculatePortfolioWeightsTool`

```python
class WeightItem(BaseModel):
    index_id: UUID
    index_name: str
    weight_pct: Decimal = Field(ge=0, le=100)
    market_value: Decimal


class CalculatePortfolioWeightsOutput(BaseModel):
    user_id: UUID
    weights: list[WeightItem]
    total_value: Decimal
    cash_weight_pct: Decimal = Field(default=Decimal("0"))
```

---

#### `CreateRecommendationTool`

```python
from nam_db.enums import AgentRole, RecommendationStatus, RecommendationType


class CreateRecommendationInput(BaseModel):
    user_id: UUID
    analysis_id: UUID
    agent: AgentRole = AgentRole.PORTFOLIO_MANAGER
    content: str = Field(min_length=50)
    type: RecommendationType
    index_id: UUID | None = None


class CreateRecommendationOutput(BaseModel):
    recommendation_id: UUID
    status: RecommendationStatus = RecommendationStatus.PENDING
    created_at: datetime
```

| Rule | Only the PM may call this tool. Always creates `Pending`. |

---

#### `CreateIndexTool`

```python
class CreateIndexInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    isin: str = Field(min_length=12, max_length=12, pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


class CreateIndexOutput(BaseModel):
    index_id: UUID
    name: str
    isin: str
    created: bool
```

| **DB access** | UPSERT `indices` ON CONFLICT (isin) |

---

### 9.2 Subagent tools

#### `CreateAnalysisTool`

```python
from nam_db.enums import AgentRole, SubAgentRole


class CreateAnalysisInput(BaseModel):
    user_id: UUID
    agent: SubAgentRole
    content: str = Field(min_length=100)


class CreateAnalysisOutput(BaseModel):
    analysis_id: UUID
    agent: AgentRole
    embedding_dimensions: int
    created_at: datetime
```

| **Pipeline** | content → embed → INSERT `analyses` |

---

#### `SearchPastAnalysesTool`

```python
from nam_db.enums import AgentRole


class SearchPastAnalysesInput(BaseModel):
    user_id: UUID
    query: str = Field(min_length=10)
    top_k: int = Field(default=5, ge=1, le=20)
    agent_filter: AgentRole | None = None
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0)


class AnalysisSearchResult(BaseModel):
    analysis_id: UUID
    agent: AgentRole
    content_snippet: str
    similarity_score: float
    created_at: datetime
```

| **DB access** | pgvector cosine similarity, filtered by `user_id` |

---

#### `GetMarketPriceTool` / `GetFinancialsNewsTool` / `GetDataFromUrlTool` / `GetCompanyFinancialsTool`

Same Pydantic schemas as v0.1. Implemented as individual classes in `agentic/tools/market/`.  
`GetCompanyFinancialsTool` is restricted to `SectorAnalystAgent`.

---

## 10. Core business flows

### 10.1 Autonomous market cycle

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant R as AgentRunner
    participant DA as Deep Agent (PM)
    participant SA as Subagents
    participant DB as PostgreSQL

    S->>R: invoke(EU, PRE_OPEN) at 08:50
    R->>DA: ainvoke + NamRuntimeContext
    DA->>DA: write_todos
    DA->>SA: task(sector-analyst)
    DA->>SA: task(macro-strategist)
    DA->>SA: task(etf-quant)
    SA->>DB: create_analysis (+ embedding)
    SA-->>DA: summaries (isolated context)
    DA->>DB: create_recommendation (PENDING)
    DA-->>R: done
```

### 10.2 Chat (optional)

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant API as API Module
    participant R as AgentRunner
    participant DA as Deep Agent
    participant DB as PostgreSQL

    U->>F: "What do you think about my ETF exposure?"
    F->>API: WS message
    API->>R: stream(message, context=chat)
    R->>DA: astream
    DA-->>R: token chunks
    R-->>API: stream chunks
    API-->>F: WS stream
    DA->>DB: create_analysis (if relevant)
```

### 10.3 User validates recommendation

```mermaid
sequenceDiagram
    participant U as User
    participant API as API Module
    participant DB as PostgreSQL

    U->>API: PATCH /recommendations/{id} {status: APPLIED}
    API->>DB: UPDATE recommendation
    API->>DB: INSERT transaction (if BUY/SELL)
    API->>DB: UPDATE position snapshot
    API-->>U: Confirmation
```

### 10.4 Feedback loop (semantic memory)

```mermaid
sequenceDiagram
    participant U as User
    participant API as API Module
    participant DB as PostgreSQL+pgvector
    participant DA as Deep Agent (future cycle)

    U->>API: PATCH recommendation REJECTED + comment
    API->>DB: UPDATE status, user_comment
    Note over DA: Next autonomous cycle
    DA->>DB: search_past_analyses("rejected ETF decision")
    DB-->>DA: Past analyses + rejection context
```

---

## 11. Non-functional requirements

### 11.1 Performance

| Metric | v1 target |
|--------|-----------|
| API latency (p95) | < 200ms (excluding LLM) |
| Single market brief cycle | < 5 min (local 7B model) |
| pgvector search (top-10) | < 100ms |
| Chat first token | < 3s |

### 11.2 Security

- JWT or session cookie authentication (v1.1)
- Agents without user API credentials
- Strict Pydantic validation on all tools
- SQLAlchemy parameterized queries only
- `GetDataFromUrlTool`: SSRF protection + domain whitelist

### 11.3 Observability

- Structured JSON logs per module
- Correlation via `request_id` / `run_id` / `market`+`phase`
- Metrics: cycle duration, LLM tokens, tool errors, scheduler trigger count

### 11.4 Configuration

| Variable | Module | Description |
|----------|--------|-------------|
| `DATABASE_URL` | All | Async PostgreSQL connection string |
| `EMBEDDING_MODEL` | Agentic | Embedding model name |
| `EMBEDDING_DIM` | Agentic + DB | Vector dimension (must match) |
| `LLM_MODEL` | Agentic | e.g. `ollama:llama3.1:8b` |
| `LLM_BASE_URL` | Agentic | Ollama/vLLM endpoint |
| `DEFAULT_USER_ID` | Agentic | User ID for autonomous cycles (v1 single-user) |
| `MARKET_TIMEZONE` | Agentic | Default: `Europe/Paris` |

---

## 12. Out of scope and future phases

| Phase | Feature |
|-------|---------|
| v1.1 | Persistent chat threads (LangGraph checkpointer) |
| v1.2 | Admin UI to adjust market hours without restart |
| v2.0 | Multi-user, RBAC |
| v2.1 | Broker integration (read-only) |
| v2.2 | Backtesting and Monte Carlo simulation |
| v2.3 | Async remote subagents (Deep Agents v0.5+) |

---

## 13. Glossary

| Term | Definition |
|------|------------|
| **Deep Agents** | LangChain agent harness — planning, subagents, filesystem, context compression |
| **Deep Agent Factory** | NAM class that assembles `create_deep_agent()` from OOP components |
| **ACB** | Average Cost Basis — mean acquisition cost per unit |
| **Ledger** | Immutable transaction log |
| **Snapshot** | Current position state, recalculated by the API |
| **Pending** | Recommendation awaiting human validation |
| **Market Phase** | `MarketPhase` enum — PRE_OPEN / POST_OPEN / PERIODIC / CLOSE / CHAT / MANUAL |
| **Runtime Context** | `NamRuntimeContext` — market, phase, user_id passed per invocation |
| **pgvector** | PostgreSQL extension for vector search |

---

## Appendix A — OpenSpec repo structure

```text
nam/
├── openspec.md
├── pyproject.toml
├── packages/db/               ← nam-db (models + alembic)
├── api/                       ← nam-api
├── agentic/                   ← nam-agentic
├── openspec/
│   ├── config.yaml
│   ├── specs/
│   └── changes/
└── .cursor/
```

### Recommended next steps

1. `/opsx:propose setup-monorepo` — scaffold `packages/db`, `api/`, `agentic/`
2. `/opsx:propose database-schema` — Alembic initial migration
3. `/opsx:propose deep-agent-core` — OOP agents + factory + tools
4. `/opsx:propose market-scheduler` — autonomous worker

---

*Nestor Asset Manager — OpenSpec master reference document.*
