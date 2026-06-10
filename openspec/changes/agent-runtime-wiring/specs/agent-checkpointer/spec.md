## ADDED Requirements

### Requirement: Agentic database URL setting
`nam_agentic/settings.py` MUST expose `database_url: str` loaded from env `DATABASE_URL` (same variable and PostgreSQL instance as `nam-db` / `nam-api`).

The checkpointer MUST use `settings.database_url` — not a separate checkpoint-only DSN unless explicitly configured later.

#### Scenario: Agentic loads shared DATABASE_URL
- **WHEN** `nam-agentic` starts with `DATABASE_URL` set in the environment
- **THEN** `settings.database_url` is available to the checkpointer factory
- **AND** agentic connects to the same Postgres instance as domain tables

### Requirement: PostgreSQL LangGraph checkpointer
`nam-agentic` MUST configure a LangGraph checkpointer backed by PostgreSQL using the same `DATABASE_URL` as `nam-db` in all environments (local development, tests, deployment). There MUST NOT be an in-memory checkpointer path (`MemorySaver` or equivalent).

The checkpointer MUST be created during FastAPI lifespan, passed into `DeepAgentFactory`, and attached via `create_deep_agent(checkpointer=...)`.

Checkpoint table setup MUST run during the FastAPI application lifespan (e.g. `await checkpointer.setup()`).

#### Scenario: Checkpointer uses shared database URL
- **WHEN** `nam-agentic` starts with a valid `DATABASE_URL`
- **THEN** the checkpointer connects to that PostgreSQL instance
- **AND** `AsyncPostgresSaver` (or project-standard async Postgres saver) is used

#### Scenario: Checkpoint tables initialized at startup
- **WHEN** the agentic lifespan context enters
- **THEN** LangGraph checkpoint tables are created or verified
- **AND** startup does not fail silently if setup fails

### Requirement: Thread-scoped conversation persistence
Agent invocations that include a `thread_id` MUST persist graph state (messages and `StateBackend` files for that thread) via the checkpointer so a subsequent invoke with the same `thread_id` continues the conversation after process restart.

#### Scenario: Chat thread survives agentic restart
- **GIVEN** a chat completed at least one turn with `thread_id=T`
- **WHEN** `nam-agentic` restarts
- **AND** a new message is sent on `/chat/stream` with `thread_id=T`
- **THEN** prior messages from thread `T` are available to the agent

#### Scenario: Market session uses dedicated thread id
- **WHEN** `market.session` invokes the agent
- **THEN** the runner supplies `thread_id=market:{market}:{phase}:{date}` per `agentic-package` spec
- **AND** market cycle checkpoint state does not overwrite chat thread state
