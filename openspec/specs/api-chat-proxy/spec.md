## Requirements

### Requirement: WebSocket chat endpoint on API
`nam-api` MUST expose a WebSocket endpoint at `/ws/chat` (or `/ws/chat/`).

The front MUST connect only to nam-api for chat — not directly to nam-agentic.

#### Scenario: WebSocket upgrade succeeds
- **WHEN** a client opens `WS {API_URL}/ws/chat`
- **THEN** the connection is accepted
- **AND** nam-api does not import `nam_agentic` as a Python module

### Requirement: API proxies stream to agentic
On each inbound WebSocket text message, nam-api MUST:

1. Parse JSON `ChatWsClientMessage` (`content`, optional `thread_id`)
2. Open an HTTP streaming request to `{AGENTIC_URL}/chat/stream`
3. Relay each `ChatStreamEvent` from agentic to the WebSocket client as JSON text frames
4. Send `type=error` if the agentic stream ends without a `done` or `error` terminal event

nam-api MUST use `httpx` (async) or equivalent — no shared Python process with agentic.

#### Scenario: Token relay
- **WHEN** agentic streams `{"type": "token", "content": "Hello"}`
- **THEN** the WebSocket client receives the same JSON payload

#### Scenario: Multiple messages on one WebSocket
- **GIVEN** an open WebSocket connection to `/ws/chat`
- **WHEN** the client sends two valid JSON messages in sequence
- **THEN** nam-api opens two separate HTTP streams to `/chat/stream` (one per message)
- **AND** token/done events for each message are relayed on the same WebSocket in order
- **AND** the second message may reuse `thread_id` from the first message's `done` event

#### Scenario: Agentic unreachable
- **WHEN** agentic is down or `/chat/stream` returns an error
- **THEN** the WebSocket client receives `{"type": "error", "message": "..."}`

#### Scenario: Truncated agentic stream
- **WHEN** the HTTP stream to agentic ends without `done` or `error`
- **THEN** the WebSocket client receives `type=error` with an interruption message

### Requirement: ChatWsClientMessage schema
`nam_api/schemas/chat.py` MUST define:

**ChatWsClientMessage**:

| Field | Type | Constraints |
|-------|------|-------------|
| `content` | str | min 1 |
| `thread_id` | str \| None | optional |

**ChatWsServerMessage**: relayed agentic `ChatStreamEvent` JSON (verbatim NDJSON lines).

#### Scenario: Invalid client message rejected
- **WHEN** the WebSocket receives non-JSON or empty `content`
- **THEN** server sends `type=error` with validation detail
- **AND** does not call agentic

### Requirement: AGENTIC_URL configuration
`nam_api/settings.py` MUST expose `agentic_url: str` (env `AGENTIC_URL`, default `http://localhost:8001`).

#### Scenario: Settings load agentic URL
- **WHEN** nam-api starts
- **THEN** chat proxy targets `settings.agentic_url`

### Requirement: WebSocket chat replaces stub
`nam_api/websocket/chat.py` MUST implement the live proxy — not a placeholder docstring only.

#### Scenario: Chat module wires router
- **WHEN** `nam_api.main` includes WebSocket routes
- **THEN** `/ws/chat` is registered and functional
