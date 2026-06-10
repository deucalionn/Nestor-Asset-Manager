## Requirements

### Requirement: Streaming chat endpoint
`nam-agentic` MUST expose `POST /chat/stream` that accepts a JSON body and returns a **streaming HTTP response** (chunked body with newline-delimited JSON events).

This endpoint MUST NOT return 202 Accepted — it MUST hold the connection until the agent run completes or errors.

`nam-api` MUST call this endpoint for chat; chat MUST NOT use `POST /events`.

#### Scenario: Stream request accepted
- **WHEN** `POST /chat/stream` is sent with valid `content` and optional `thread_id`
- **THEN** the response status is 200
- **AND** the response body is a stream of events
- **AND** the connection remains open until a terminal event

#### Scenario: Chat does not use event bus
- **WHEN** a user sends a chat message through the API WebSocket proxy
- **THEN** nam-api calls `/chat/stream` on agentic
- **AND** does not send `type=chat.message` to `POST /events`

### Requirement: ChatStreamRequest schema
`nam_agentic` MUST define Pydantic schemas for the chat stream API:

**ChatStreamRequest**:

| Field | Type | Constraints |
|-------|------|-------------|
| `content` | str | min 1, max 16000 |
| `thread_id` | str \| None | optional; server generates UUID if omitted |
| `user_id` | UUID \| None | optional; defaults to `settings.default_user_id` |

**ChatStreamEvent** (each streamed line):

| Field | Type | Notes |
|-------|------|-------|
| `type` | literal | `token`, `status`, `done`, `error` |
| `content` | str \| None | token text when `type=token` |
| `status` | literal \| None | `thinking`, `tool`, `writing` when `type=status` |
| `tool` | str \| None | human label when `type=status` and `status=tool` |
| `thread_id` | str \| None | set on `done` |
| `message` | str \| None | error detail when `type=error` |

`status` events are UX progress signals relayed by the API proxy; the front MAY display them while waiting for tokens.

#### Scenario: New thread receives id on completion
- **WHEN** `POST /chat/stream` is called without `thread_id`
- **THEN** the stream includes a `done` event with a new `thread_id`
- **AND** subsequent requests with that `thread_id` continue the conversation

### Requirement: Chat stream invokes AgentRunner with CHAT phase
`/chat/stream` MUST call `AgentRunner.stream_events()` (or equivalent streaming entry point) with `NamRuntimeContext(phase=MarketPhase.CHAT, thread_id=..., user_id=...)`.

#### Scenario: Runtime context for chat
- **WHEN** `/chat/stream` processes a message
- **THEN** the runner receives `phase=CHAT`
- **AND** `thread_id` is passed to LangGraph config `configurable.thread_id`

### Requirement: ChatStreamRouter registration
The chat stream route MUST be registered on the nam-agentic FastAPI app alongside `/health` and `/events`.

#### Scenario: OpenAPI lists chat stream
- **WHEN** agentic OpenAPI schema is generated
- **THEN** `POST /chat/stream` is documented
