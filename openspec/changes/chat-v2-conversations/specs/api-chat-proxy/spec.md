## MODIFIED Requirements

### Requirement: API proxies stream to agentic
On each inbound WebSocket text message, nam-api MUST:

1. Parse JSON `ChatWsClientMessage` (`content`, optional `thread_id`)
2. Open an HTTP streaming request to `{AGENTIC_URL}/chat/stream`
3. Relay each `ChatStreamEvent` from agentic to the WebSocket client as JSON text frames **verbatim** (including `thread_id` on every event)
4. Send `type=error` if the agentic stream ends without a `done` or `error` terminal event

nam-api MUST use `httpx` (async) or equivalent — no shared Python process with agentic.

#### Scenario: Token relay preserves thread_id
- **WHEN** agentic streams `{"type": "token", "content": "Hello", "thread_id": "abc"}`
- **THEN** the WebSocket client receives the same JSON payload including `thread_id`

#### Scenario: Multiple messages on one WebSocket
- **GIVEN** an open WebSocket connection to `/ws/chat`
- **WHEN** the client sends two valid JSON messages in sequence (possibly different `thread_id` values)
- **THEN** nam-api opens two separate HTTP streams to `/chat/stream`
- **AND** events for each stream are relayed in order with correct per-event `thread_id`

#### Scenario: Agentic unreachable
- **WHEN** agentic is down or `/chat/stream` returns an error
- **THEN** the WebSocket client receives `{"type": "error", "message": "..."}`

#### Scenario: Truncated agentic stream
- **WHEN** the HTTP stream to agentic ends without `done` or `error`
- **THEN** the WebSocket client receives `type=error` with an interruption message
