## ADDED Requirements

### Requirement: Event-driven agent activation
While `nam-agentic` is running, the process MUST remain idle between events — there is MUST NOT be a continuous LLM loop.

The agent MUST run only when `EventHandler` receives an event that invokes `AgentRunner` (e.g. `market.session`, `chat.message`, profile lifecycle events).

APScheduler cron jobs that enqueue `news.ingest.*` events MUST NOT invoke `AgentRunner` — they perform I/O and database upsert only.

#### Scenario: Service idle between market events
- **GIVEN** `nam-agentic` is running
- **AND** no event is being processed
- **WHEN** wall clock time passes
- **THEN** no LLM invocation occurs until the next event is handled

#### Scenario: News ingest does not wake the agent
- **WHEN** `news.ingest.session` is handled
- **THEN** `NewsIngestService` runs
- **AND** `AgentRunner.invoke()` is not called

### Requirement: AgentRunner invocation on market session
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

## MODIFIED Requirements

### Requirement: EventHandler extension points
`EventHandler` MUST route events by type to dedicated handler methods.

`_on_market_session` MUST invoke `AgentRunner` (not remain a log-only stub).

`_on_news_ingest_daily`, `_on_news_ingest_session`, and other non-agent handlers MUST NOT invoke `AgentRunner`.

Profile and chat handlers SHOULD invoke `AgentRunner` when implemented; until then they MAY remain log-only stubs without blocking calendar work.

#### Scenario: Handler dispatches by type
- **GIVEN** an `AgentEvent` with `type=user.profile.created`
- **WHEN** `EventHandler.handle()` runs
- **THEN** `_on_user_profile_created` is invoked
- **AND** the agent workspace directory exists (created if missing)

#### Scenario: Market session is not a stub
- **GIVEN** an `AgentEvent` with `type=market.session`
- **WHEN** `EventHandler.handle()` runs
- **THEN** `_on_market_session` invokes `AgentRunner.invoke()`

## REMOVED Requirements

### Requirement: Out of scope — AgentRunner wiring
**Reason**: Superseded by this change — minimal `AgentRunner.invoke()` wiring on `market.session` is now in scope so calendar and autonomous cycles can run.

**Migration**: Implement `_on_market_session` → `AgentRunner` in `EventHandler`; inject runner via `dependencies.py`.
