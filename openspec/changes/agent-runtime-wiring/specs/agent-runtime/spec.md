## MODIFIED Requirements

### Requirement: Event-driven agent activation
While `nam-agentic` is running, the process MUST remain idle between events — there MUST NOT be a continuous LLM loop.

The agent MUST run only when `EventHandler` receives an event that invokes `AgentRunner`, or when `/chat/stream` handles a user message.

Events that invoke the agent: `market.session`, `user.profile.created`, `user.profile.updated`.

Chat user messages MUST use `POST /chat/stream` (via API WebSocket proxy) — NOT `POST /events` with `type=chat.message`.

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

### Requirement: EventHandler extension points
`EventHandler` MUST route events by type to dedicated handler methods.

`_on_market_session` MUST invoke `AgentRunner`.

`_on_user_profile_created` and `_on_user_profile_updated` MUST invoke `AgentRunner.invoke()` with `NamRuntimeContext(phase=MANUAL)` and an onboarding or profile-refresh seed message.

There MUST NOT be an `_on_chat_message` handler that invokes the agent — chat is handled exclusively by `/chat/stream`.

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

#### Scenario: Chat message event does not invoke via EventHandler
- **GIVEN** a request to `POST /events` with unknown or legacy chat payload
- **WHEN** the event type is not a supported agent event
- **THEN** `AgentRunner.invoke()` is not called
- **AND** chat is expected only through `/chat/stream`

## ADDED Requirements

### Requirement: Onboarding agent seed message
`EventHandler._on_user_profile_created` MUST invoke the agent with a seed message instructing the Portfolio Manager to:

1. Call `get_user_context` (profile already persisted by nam-api via `POST /setup`)
2. Write interpreted goals and strategy to `/user/{user_id}/USER_GOALS.md` via `write_file`
3. Summarize the user profile for future cycles

The agent MUST NOT create or mutate the user row in PostgreSQL — workspace files only.

#### Scenario: Onboarding writes user goals file
- **WHEN** `user.profile.created` is processed and the agent run completes
- **THEN** a file exists at `{agent_workspace_dir}/user/{user_id}/USER_GOALS.md` on the volume
- **AND** the file is non-empty

### Requirement: Profile update agent seed message
`EventHandler._on_user_profile_updated` MUST invoke the agent with a seed message instructing the Portfolio Manager to:

1. Call `get_user_context` for the updated profile
2. **Rewrite** (replace entire contents of) `/user/{user_id}/USER_GOALS.md` via `write_file` — not append-only
3. Summarize what changed for future cycles

The API continues to own profile persistence in PostgreSQL (`PUT /profile`); the agent only refreshes workspace interpretation files.

#### Scenario: Profile update rewrites goals file
- **WHEN** `user.profile.updated` is processed and the agent run completes
- **THEN** `/user/{user_id}/USER_GOALS.md` reflects the updated profile from `get_user_context`
- **AND** the file is non-empty

### Requirement: chat.message removed from event bus
`EventType` MUST NOT include `chat.message`. Inbound user chat MUST use only the API WebSocket proxy → `POST /chat/stream` path.

If legacy clients send unknown event types to `POST /events`, they MUST be rejected or ignored — not routed to `AgentRunner`.

#### Scenario: EventType has no chat variant
- **WHEN** `nam_agentic/schemas/events.py` is reviewed
- **THEN** `CHAT_MESSAGE` / `chat.message` is absent from `EventType`
- **AND** `EventHandler` has no chat invoke path

## REMOVED Requirements

### Requirement: Out of scope — WebSocket chat proxy on nam-api
**Reason**: Chat proxy is now in scope via `api-chat-proxy` capability.

**Migration**: Implement `/ws/chat` on nam-api and `/chat/stream` on agentic.

### Requirement: Out of scope — Writing USER_GOALS.md or other workspace content
**Reason**: Onboarding agent run now writes workspace files; prompts remain hand-owned but invoke wiring is in scope.

**Migration**: Wire `_on_user_profile_created` → `AgentRunner.invoke()` with onboarding seed.
