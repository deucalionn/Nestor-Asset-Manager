# Agent runtime — requirements

Scope: **architecture plumbing and event-driven activation**. Deep Agent graph, subagents, tools, and workspace file content are **hand-implemented** by the project owner.

## Requirement: Standalone agent FastAPI service

`nam-agentic` MUST expose a FastAPI application on port **8001** (configurable), separate from `nam-api`.

##### Scenario: Health check
- GIVEN `nam-agentic` is running
- WHEN `GET /health` is called
- THEN the response status is 200
- AND the body includes `"service": "nam-agentic"`

## Requirement: Event bus entry point

`nam-agentic` MUST accept inbound events at `POST /events` and return **202 Accepted** before async processing.

##### Scenario: Market session event accepted
- GIVEN `nam-agentic` is running
- WHEN `POST /events` is sent with `type=market.session` and payload `{market, phase}`
- THEN the response status is 202
- AND the event is dispatched to `EventHandler` asynchronously

Supported event types (enum):

| Type | Source |
|------|--------|
| `user.profile.created` | nam-api after `POST /setup` |
| `user.profile.updated` | nam-api after `PUT /profile` |
| `market.session` | APScheduler cron inside agentic lifespan |
| `news.ingest.session` | APScheduler cron inside agentic lifespan |

User chat MUST use `POST /chat/stream` (via API WebSocket proxy) — not `POST /events`.

## Requirement: Market scheduler in app lifespan

APScheduler MUST start and stop with the FastAPI application lifespan — **no standalone worker process**.

##### Scenario: Cron registration at startup
- GIVEN `nam-agentic` starts
- WHEN the lifespan context enters
- THEN cron jobs are registered for EU, US, and ASIA sessions
- AND each trigger enqueues a `market.session` event

Phases per market (see `openspec.md` §7.2): PRE_OPEN, POST_OPEN, PERIODIC, CLOSE.

## Requirement: API notifies agentic via HTTP

`nam-api` MUST NOT import `nam-agentic` as a Python dependency. Profile lifecycle events MUST be sent via HTTP to `AGENTIC_URL`.

##### Scenario: Setup notifies agentic
- GIVEN `AGENTIC_URL` points to a running agentic service
- WHEN `POST /setup` succeeds
- THEN nam-api sends `user.profile.created` to agentic `/events`
- AND setup still succeeds if agentic is unreachable (logged warning only)

## Requirement: Event-driven agent activation

While `nam-agentic` is running, the process MUST remain idle between events — there MUST NOT be a continuous LLM loop.

The agent MUST run only when `EventHandler` receives an event that invokes `AgentRunner`, or when `/chat/stream` handles a user message.

Events that invoke the agent: `market.session`, `user.profile.created`, `user.profile.updated`.

APScheduler cron jobs that enqueue `news.ingest.*` events MUST NOT invoke `AgentRunner` — they perform I/O and database upsert only.

#### Scenario: Service idle between market events
- **GIVEN** `nam-agentic` is running
- **AND** no event is being processed
- **AND** no active `/chat/stream` request
- **WHEN** wall clock time passes
- **THEN** no LLM invocation occurs until the next event or chat request

#### Scenario: News ingest does not wake the agent
- **WHEN** `news.ingest.session` is handled
- **THEN** `NewsIngestService` runs
- **AND** `AgentRunner.invoke()` is not called

## Requirement: AgentRunner invocation on market session

`EventHandler._on_market_session` MUST call `AgentRunner.invoke()` with a `NamRuntimeContext` built from the event payload (`market`, `phase`) and a cycle seed message.

This invocation is the trigger for autonomous portfolio cycles, including calendar refresh by the Portfolio Manager.

There MUST NOT be a separate APScheduler job or cron dedicated to calendar fetch or calendar file writes.

#### Scenario: PRE_OPEN cron wakes the PM agent
- **WHEN** APScheduler enqueues `market.session` with `{market: EU, phase: PRE_OPEN}`
- **AND** `EventHandler.handle()` processes the event
- **THEN** `AgentRunner.invoke()` is called once
- **AND** `NamRuntimeContext` includes `market=EU` and `phase=PRE_OPEN`

#### Scenario: No calendar-specific cron exists
- **WHEN** APScheduler jobs registered at startup are reviewed
- **THEN** no job exists whose sole purpose is fetching Boursorama calendar pages
- **AND** calendar refresh occurs only inside agent runs triggered by other events (typically `market.session`)

## Requirement: EventHandler extension points

`EventHandler` MUST route events by type to dedicated handler methods.

`_on_market_session` MUST invoke `AgentRunner`.

`_on_user_profile_created` and `_on_user_profile_updated` MUST invoke `AgentRunner.invoke()` with `NamRuntimeContext(phase=MANUAL)` and an onboarding or profile-refresh seed message.

There MUST NOT be an `_on_chat_message` handler — chat is handled exclusively by `/chat/stream`.

`_on_news_ingest_session` and other non-agent handlers MUST NOT invoke `AgentRunner`.

#### Scenario: Handler dispatches by type
- **GIVEN** an `AgentEvent` with `type=user.profile.created`
- **WHEN** `EventHandler.handle()` runs
- **THEN** `_on_user_profile_created` is invoked
- **AND** the agent workspace directory exists (created if missing)
- **AND** `AgentRunner.invoke()` is called

#### Scenario: Market session is not a stub
- **GIVEN** an `AgentEvent` with `type=market.session`
- **WHEN** `EventHandler.handle()` runs
- **THEN** `_on_market_session` invokes `AgentRunner.invoke()`

#### Scenario: Profile update triggers agent run
- **GIVEN** an `AgentEvent` with `type=user.profile.updated`
- **WHEN** `EventHandler.handle()` runs
- **THEN** `_on_user_profile_updated` invokes `AgentRunner.invoke()`

## Requirement: Onboarding agent seed message

`EventHandler._on_user_profile_created` MUST invoke the agent with a seed message instructing the Portfolio Manager to:

1. Call `get_user_context` (profile already persisted by nam-api via `POST /setup`)
2. Write interpreted goals and strategy to `/user/{user_id}/USER_GOALS.md` via `write_file`
3. Summarize the user profile for future cycles

The agent MUST NOT create or mutate the user row in PostgreSQL — workspace files only.

#### Scenario: Onboarding writes user goals file
- **WHEN** `user.profile.created` is processed and the agent run completes
- **THEN** a file exists at `{agent_workspace_dir}/user/{user_id}/USER_GOALS.md` on the volume
- **AND** the file is non-empty

## Requirement: Profile update agent seed message

`EventHandler._on_user_profile_updated` MUST invoke the agent with a seed message instructing the Portfolio Manager to:

1. Call `get_user_context` for the updated profile
2. **Rewrite** `/user/{user_id}/USER_GOALS.md` via `write_file`
3. Summarize what changed for future cycles

#### Scenario: Profile update rewrites goals file
- **WHEN** `user.profile.updated` is processed and the agent run completes
- **THEN** `/user/{user_id}/USER_GOALS.md` reflects the updated profile from `get_user_context`
- **AND** the file is non-empty

## Requirement: chat.message removed from event bus

`EventType` MUST NOT include `chat.message`. Inbound user chat MUST use only the API WebSocket proxy → `POST /chat/stream` path.

#### Scenario: EventType has no chat variant
- **WHEN** `nam_agentic/schemas/events.py` is reviewed
- **THEN** `CHAT_MESSAGE` / `chat.message` is absent from `EventType`
- **AND** `EventHandler` has no chat invoke path

## Requirement: News ingest scheduler jobs

In addition to `market.session` cron jobs, `nam-agentic` lifespan MUST register **session news ingest** — `news.ingest.session` at EU POST_OPEN (09:20), first mid PERIODIC (13:20), and CLOSE (17:30) Europe/Paris.

There MUST NOT be a `news.ingest.daily` cron job.

#### Scenario: News jobs registered at startup
- **WHEN** `nam-agentic` lifespan enters
- **THEN** APScheduler has jobs for three EU `news.ingest.session` triggers
- **AND** jobs are removed on lifespan shutdown

## Requirement: News ingest event dispatch

`POST /events` MUST accept `news.ingest.session` and return 202 before async processing.

#### Scenario: Session ingest event accepted
- **WHEN** `POST /events` is sent with `type=news.ingest.session` and payload `{market: "EU"}`
- **THEN** the response status is 202
- **AND** `EventHandler` invokes the news ingest handler without `AgentRunner`

## Out of scope (hand-owned)

- Subagent classes, tool implementations, prompt prose content
- Docker Compose full stack (separate change)
