# Agent runtime — requirements (skeleton)

Scope: **architecture plumbing only**. Deep Agent graph, subagents, tools, and workspace file content are **hand-implemented** by the project owner — not part of this change.

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
| `chat.message` | nam-api WebSocket (future) |
| `market.session` | APScheduler cron inside agentic lifespan |

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

## Requirement: EventHandler extension points

`EventHandler` MUST route events by type to dedicated handler methods. Each method is a **stub hook** until the owner wires `AgentRunner`.

##### Scenario: Handler dispatches by type
- GIVEN an `AgentEvent` with `type=user.profile.created`
- WHEN `EventHandler.handle()` runs
- THEN `_on_user_profile_created` is invoked
- AND the agent workspace directory exists (created if missing)

## Out of scope (hand-owned)

- `DeepAgentFactory`, subagent classes, tool implementations
- `AgentRunner.invoke()` / `stream()` wiring
- Writing `USER_GOALS.md` or other workspace content
- WebSocket chat proxy on nam-api
