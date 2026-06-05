## Context

NAM is a greenfield project. `openspec.md` v0.2.0 defines the full architecture (monorepo, Deep Agents, autonomous scheduler, OOP conventions) but the repository currently contains only OpenSpec configuration and documentation — no Python code.

This change scaffolds the **executable skeleton**: uv workspace, three packages, dev infrastructure. It does not implement business logic, database migrations with tables, or working agent tools.

## Goals / Non-Goals

**Goals:**
- uv workspace with `nam-db`, `nam-api`, `nam-agentic` as editable members
- Shared `packages/db` with SQLAlchemy async base, enums, `settings.py`, session factory, Alembic config, model stubs
- FastAPI skeleton with `/health`
- Agentic OOP skeleton: `BaseSubAgent`, `BaseNamTool`, `DeepAgentFactory`, `AgentRunner`, scheduler stub
- docker-compose PostgreSQL + pgvector for local dev
- `.env.example`, `.gitignore`, `README.md`, `justfile` with setup instructions
- All structural decisions aligned with `openspec.md`

**Non-Goals:**
- Initial Alembic migration with actual tables (next change: `database-schema`)
- Working Deep Agent tools or LLM integration
- WebSocket chat implementation
- APScheduler with real market triggers
- Authentication, CRUD endpoints, frontend
- CI/CD pipeline

## Decisions

### D1 — uv workspace over poetry/pip

**Choice**: uv workspace at repo root.

**Rationale**: User requirement. uv is faster, has native workspace support, and handles lockfiles per package cleanly.

**Structure**:
```text
nam/
├── pyproject.toml              # [tool.uv.workspace] members
├── uv.lock
├── packages/db/pyproject.toml  # name = "nam-db"
├── api/pyproject.toml          # name = "nam-api"
└── agentic/pyproject.toml      # name = "nam-agentic"
```

**Alternatives considered**:
- *poetry with path deps* — works but user chose uv
- *single pyproject.toml* — rejected; loses package boundary enforcement

### D2 — `packages/db` as shared kernel

**Choice**: All ORM models, enums, session, Alembic in `packages/db/nam_db/`.

**Rationale**: Single migration history, single enum source, both `api/` and `agentic/` import the same models.

**Alembic location**: `packages/db/alembic/` with `alembic.ini` at `packages/db/alembic.ini`.

**Alembic async setup**: initialized with the official async template:
```bash
cd packages/db && alembic init -t async alembic
```
This generates an `env.py` with `async_engine_from_config` + `run_async_migrations()`. Must NOT use the default sync template.

**PostgreSQL enums in migrations**: use [`alembic-postgresql-enum`](https://github.com/Pogchamp-company/alembic-postgresql-enum) so native ENUM types are tracked in autogenerate and revision files.

```python
# packages/db/alembic/env.py (after init)
from alembic_postgresql_enum import configure

configure()  # register enum autogenerate hooks
```

```python
# packages/db/nam_db/models/example.py
from sqlalchemy import Enum as SAEnum
from nam_db.enums import AgentRole

agent: Mapped[AgentRole] = mapped_column(
    SAEnum(AgentRole, name="agent_enum", create_constraint=True, native_enum=True),
    nullable=False,
)
```

**Dependencies** (packages/db/pyproject.toml): `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `alembic-postgresql-enum`, `pgvector`

**Alternatives considered**:
- *Separate alembic at root* — rejected; splits DB concerns from models
- *Duplicate models per package* — rejected; divergence risk
- *Sync Alembic template* — rejected; app uses async sessions exclusively
- *Manual enum DDL in migrations* — rejected; error-prone, alembic-postgresql-enum handles autogenerate

### D3 — Dependency graph

```text
nam-db  ◄──  nam-agentic  ◄──  nam-api
```

- `nam-api` depends on both `nam-db` and `nam-agentic` (chat in-process)
- `nam-agentic` depends only on `nam-db`
- `nam-db` has zero internal workspace deps

Enforced via uv path dependencies in each `pyproject.toml`:
```toml
[tool.uv.sources]
nam-db = { workspace = true }
nam-agentic = { workspace = true }
```

### D4 — OOP agent architecture (stubs in this change)

**Choice**: Class-based agents with abstract bases, not dict configs.

```text
agents/base.py          → BaseSubAgent (ABC)
agents/portfolio_manager.py → PortfolioManagerAgent
agents/sector_analyst.py    → SectorAnalystAgent
agents/macro_strategist.py  → MacroStrategistAgent
agents/etf_quant.py         → EtfQuantSpecialistAgent

tools/base.py           → BaseNamTool (ABC)
tools/registry.py       → ToolRegistry (DI container, stub)

prompts/loader.py       → PromptLoader (reads {NAME}.md)
prompts/PORTFOLIO.md    → PM system prompt
prompts/SECTOR_ANALYST.md
prompts/MACRO_STRATEGIST.md
prompts/ETF_QUANT.md

factory.py              → DeepAgentFactory
runner.py               → AgentRunner
```

`BaseSubAgent.to_spec()` is the **only** adapter to Deep Agents — it returns a typed `SubAgent(...)` spec for `create_deep_agent(subagents=[...])`.

**Alternatives considered**:
- *Raw dict subagent configs* — rejected per openspec.md OOP convention
- *Full tool implementation now* — deferred to next changes

### D5 — Deep Agents harness

**Choice**: `create_deep_agent()` from `deepagents` package. No manual `StateGraph`.

`DeepAgentFactory.build()` assembles:
```python
create_deep_agent(
    model=settings.llm_model,          # e.g. "ollama:llama3.1:8b"
    system_prompt=pm.system_prompt(),
    tools=pm.tools(),
    subagents=[a.to_spec() for a in subagents],
)
```

In this change, tools are stubs returning placeholder strings.

### D6 — Runtime context pattern

**Choice**: `NamRuntimeContext` frozen dataclass passed to `AgentRunner.invoke/stream()`.

Runtime-only enums (`Market`, `MarketPhase`) live in `nam_agentic/enums.py` — not in `nam_db` since they are not persisted yet.

DB-backed enums live in `nam_db/enums.py` — imported by both API schemas and agentic tools.

### D7 — Scheduler stub

**Choice**: `scheduler/markets.py` defines `MarketSession` dataclass with EU/US/ASIA hours. `scheduler/worker.py` is a runnable stub that logs startup — real APScheduler registration deferred.

Market hours (Europe/Paris):
| Market | Open | Close |
|--------|------|-------|
| EU | 09:00 | 17:30 |
| US | 15:30 | 22:00 |
| ASIA | 02:00 | 08:00 |

Check rhythm (from openspec.md): PRE_OPEN (−10min), POST_OPEN (+20min), PERIODIC (every 2h), CLOSE.

### D8 — Dev infrastructure

**Choice**: docker-compose with `pgvector/pgvector:pg16` image. pgvector extension auto-created via init script.

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    ports: ["5432:5432"]
    environment:
      POSTGRES_USER: nam
      POSTGRES_PASSWORD: nam
      POSTGRES_DB: nam
    volumes:
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/01-init.sql
```

```sql
-- docker/postgres/init.sql
CREATE EXTENSION IF NOT EXISTS vector;
```

`DATABASE_URL=postgresql+asyncpg://nam:nam@localhost:5432/nam`

### D9 — Embedding dimension default

**Choice**: Default `EMBEDDING_DIM=384` in `.env.example` (nomic-embed-text compatible). Final choice documented as open question — does not block scaffolding.

### D10 — Python 3.12+

**Choice**: Minimum Python 3.12 for modern typing (`type` statements, improved asyncio).

### D11 — Centralized settings (`pydantic-settings`)

**Choice**: Each package owns a `Settings` class via `pydantic-settings`. Database URL lives in `nam-db` and is reused by Alembic.

```text
nam_db/settings.py       → DATABASE_URL (shared kernel)
nam_api/settings.py      → API host/port, extends or imports db settings
nam_agentic/settings.py  → LLM_MODEL, LLM_BASE_URL, EMBEDDING_*, DEFAULT_USER_ID, MARKET_TIMEZONE
```

Alembic `env.py` imports `DATABASE_URL` from `nam_db.settings` — same source as `nam_db/session.py`.

**Alternatives considered**:
- *Single root settings module* — rejected; couples packages unnecessarily
- *os.environ scattered* — rejected; untestable, error-prone

## Package file tree (target state after this change)

```text
nam/
├── pyproject.toml
├── uv.lock
├── justfile                     # dev commands: sync, up, migrate, api, worker, lint
├── docker-compose.yml
├── docker/
│   └── postgres/
│       └── init.sql             # CREATE EXTENSION vector
├── .env.example
├── .gitignore
├── README.md
├── packages/db/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   └── nam_db/
│       ├── __init__.py
│       ├── base.py
│       ├── settings.py          # DATABASE_URL via pydantic-settings
│       ├── session.py
│       ├── enums.py
│       └── models/
│           ├── __init__.py
│           ├── user.py
│           ├── index.py
│           ├── transaction.py
│           ├── position.py
│           ├── analysis.py
│           └── recommendation.py
├── api/
│   ├── pyproject.toml
│   └── nam_api/
│       ├── __init__.py
│       ├── main.py
│       ├── settings.py          # API-specific settings
│       ├── routers/
│       │   ├── __init__.py
│       │   └── health.py
│       ├── services/
│       │   └── __init__.py
│       ├── schemas/
│       │   └── __init__.py
│       └── websocket/
│           ├── __init__.py
│           └── chat.py
└── agentic/
    ├── pyproject.toml
    └── nam_agentic/
        ├── __init__.py
        ├── factory.py
        ├── runner.py
        ├── context.py
        ├── settings.py          # LLM, embedding, scheduler settings
        ├── enums.py
        ├── agents/
        │   ├── __init__.py
        │   ├── base.py
        │   ├── portfolio_manager.py
        │   ├── sector_analyst.py
        │   ├── macro_strategist.py
        │   └── etf_quant.py
        ├── prompts/
        │   ├── loader.py
        │   ├── PORTFOLIO.md
        │   ├── SECTOR_ANALYST.md
        │   ├── MACRO_STRATEGIST.md
        │   └── ETF_QUANT.md
        ├── tools/
        │   ├── __init__.py
        │   ├── base.py
        │   ├── registry.py
        │   ├── portfolio/
        │   │   └── __init__.py
        │   └── market/
        │       └── __init__.py
        └── scheduler/
            ├── __init__.py
            ├── markets.py
            └── worker.py
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| uv workspace path deps break on Windows | Use forward slashes in pyproject.toml; test on macOS (primary dev env) |
| `nam-api` → `nam-agentic` coupling for chat | Acceptable for v1 local; extract to HTTP service later if needed |
| Stub tools may hide import errors until real implementation | Factory.build() called in a smoke test task |
| pgvector extension not auto-created | Init script `docker/postgres/init.sql` mounted in docker-compose |
| Deep Agents API may change | Pin `deepagents` version in pyproject.toml |

## Migration Plan

Greenfield — no migration needed. Setup sequence:
1. `uv sync` at root
2. `docker compose up -d` (pgvector extension created automatically)
3. `just migrate` or `uv run --directory packages/db alembic upgrade head`
4. `just api` or `uv run uvicorn nam_api.main:app --reload`
5. `just worker` or `uv run python -m nam_agentic.scheduler.worker`

## Open Questions

1. **Embedding dimension**: 384 (nomic-embed) vs 1024 (bge-large) — decide in `database-schema` change
2. **Asia market hours**: refine Tokyo/HK window in `market-scheduler` change
