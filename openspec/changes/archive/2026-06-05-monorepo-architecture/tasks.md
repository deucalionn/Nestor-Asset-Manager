> **Roadmap**: `[1] monorepo-architecture` (this change — skeleton) → `[2] database-schema` (tables + migration) → `[3] deep-agent-core` (tools + factory) → `[4] market-scheduler` (APScheduler live) → `[5] api-crud` (endpoints)

> **Scope reminder**: This change scaffolds structure only — no business logic, no real tools, no DB tables yet.

## 1. Root workspace setup

- [x] 1.1 Create root `pyproject.toml` with `[tool.uv.workspace]` members: `packages/db`, `api`, `agentic`
- [x] 1.2 Set Python ≥ 3.12 constraint at workspace root
- [x] 1.3 Add shared dev dependencies at root: `ruff`, `pytest`, `pytest-asyncio`, `mypy`, `just` (optional runner)
- [x] 1.4 Run `uv sync` and verify `uv.lock` is generated
- [x] 1.5 Create `.gitignore` (`.env`, `.venv`, `__pycache__`, `.pytest_cache`, `*.pyc`)
- [x] 1.6 Create root `justfile` with commands: `sync`, `up`, `down`, `migrate`, `api`, `worker`, `lint`

## 2. Shared database package (`nam-db`)

- [x] 2.1 Create `packages/db/pyproject.toml` with name `nam-db` and deps: `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `alembic-postgresql-enum`, `pgvector`, `pydantic-settings`
- [x] 2.2 Implement `nam_db/base.py` — `DeclarativeBase` subclass
- [x] 2.3 Implement `nam_db/enums.py` — `Strategy`, `TransactionType`, `AgentRole`, `SubAgentRole`, `RecommendationType`, `RecommendationStatus`
- [x] 2.4 Implement `nam_db/settings.py` — `Settings` class with `DATABASE_URL` via pydantic-settings (loaded from `.env`)
- [x] 2.5 Implement `nam_db/session.py` — async engine + `async_sessionmaker` reading `DATABASE_URL` from `nam_db.settings`
- [x] 2.6 Create model stub modules under `nam_db/models/` (user, index, transaction, position, analysis, recommendation) with `__init__.py` re-exports
- [x] 2.7 Initialize Alembic with async template: `cd packages/db && alembic init -t async alembic`
- [x] 2.8 Wire `alembic/env.py`: import all models, call `alembic_postgresql_enum.configure()`, import `DATABASE_URL` from `nam_db.settings`
- [x] 2.9 Verify `env.py` uses `async_engine_from_config` + `run_async_migrations()` (no sync engine)
- [x] 2.10 Verify `uv run --directory packages/db alembic current` runs without import errors

## 3. API package (`nam-api`)

- [x] 3.1 Create `api/pyproject.toml` with name `nam-api` and workspace deps on `nam-db`, `nam-agentic`; runtime deps: `fastapi`, `uvicorn[standard]`, `pydantic-settings`
- [x] 3.2 Implement `nam_api/settings.py` — API-specific settings (host, port); imports `DATABASE_URL` from `nam_db.settings`
- [x] 3.3 Implement `nam_api/main.py` — FastAPI app factory, include routers
- [x] 3.4 Implement `nam_api/routers/health.py` — `GET /health` returning `{"status": "ok"}`
- [x] 3.5 Create stub directories: `services/`, `schemas/`, `websocket/chat.py` (placeholder docstring)
- [x] 3.6 Verify `uv run uvicorn nam_api.main:app` starts and `/health` returns 200

## 4. Agentic package (`nam-agentic`)

- [x] 4.1 Create `agentic/pyproject.toml` with name `nam-agentic` and workspace dep on `nam-db`; runtime deps: `deepagents`, `langchain-ollama`, `apscheduler`, `pydantic-settings`
- [x] 4.2 Implement `nam_agentic/settings.py` — `LLM_MODEL`, `LLM_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `DEFAULT_USER_ID`, `MARKET_TIMEZONE`
- [x] 4.3 Implement `nam_agentic/enums.py` — `Market`, `MarketPhase`
- [x] 4.4 Implement `nam_agentic/context.py` — frozen `NamRuntimeContext` dataclass
- [x] 4.5 Implement `nam_agentic/agents/base.py` — `BaseSubAgent` ABC with `name`, `description`, `prompt_file`, `tools()`, `to_spec()`
- [x] 4.6 Implement subagent classes: `SectorAnalystAgent`, `MacroStrategistAgent`, `EtfQuantSpecialistAgent`
- [x] 4.7 Implement `PortfolioManagerAgent` in `agents/portfolio_manager.py`
- [x] 4.8 Implement `nam_agentic/prompts/loader.py` — `PromptLoader` reads `{NAME}.md`
- [x] 4.9 Implement markdown prompts: `PORTFOLIO.md`, `SECTOR_ANALYST.md`, `MACRO_STRATEGIST.md`, `ETF_QUANT.md`
- [x] 4.10 Implement `nam_agentic/tools/base.py` — `BaseNamTool` ABC with `as_tool()`
- [x] 4.11 Implement `nam_agentic/tools/registry.py` — `ToolRegistry` stub (empty tool list OK for now)
- [x] 4.12 Implement `nam_agentic/factory.py` — `DeepAgentFactory.build()` calling `create_deep_agent()`
- [x] 4.13 Implement `nam_agentic/runner.py` — `AgentRunner` with `invoke()` and `stream()` stubs
- [x] 4.14 Implement `nam_agentic/scheduler/markets.py` — `MarketSession` dataclass with EU/US/ASIA hours
- [x] 4.15 Implement `nam_agentic/scheduler/worker.py` — runnable stub with startup log
- [x] 4.16 Verify `uv run python -m nam_agentic.scheduler.worker` runs without error
- [x] 4.17 Verify no `StateGraph` imports exist in `agentic/`

## 5. Dev infrastructure

- [x] 5.1 Create `docker-compose.yml` with `pgvector/pgvector:pg16` service
- [x] 5.2 Create `docker/postgres/init.sql` with `CREATE EXTENSION IF NOT EXISTS vector;`
- [x] 5.3 Mount init script in docker-compose via `docker-entrypoint-initdb.d`
- [x] 5.4 Create `.env.example` with all documented environment variables
- [x] 5.5 Write root `README.md` with setup steps: uv install, `just sync`, `just up`, `just migrate`, `just api`, `just worker`
- [x] 5.6 Document that pgvector is auto-created on first `docker compose up`

## 6. Verification

- [x] 6.1 Run `uv sync` from root — all packages install cleanly
- [x] 6.2 Run `uv tree` — confirm dependency direction: nam-db ← nam-agentic ← nam-api
- [x] 6.3 Run `uv run ruff check .` — no lint errors on scaffolded code
- [x] 6.4 Run `docker compose up -d` + `GET /health` — returns 200
- [x] 6.5 Verify pgvector extension exists: `SELECT * FROM pg_extension WHERE extname = 'vector';`
- [x] 6.6 Smoke test: `DeepAgentFactory(...).build()` returns a compiled graph without exception
