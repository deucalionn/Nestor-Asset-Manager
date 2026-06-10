## ADDED Requirements

### Requirement: Checkpoint message history endpoint
`nam-agentic` MUST expose `GET /chat/threads/{thread_id}/messages` with query param `limit` (default 100, max 200).

The handler MUST:

1. Reject `thread_id` values starting with `market:`
2. Load graph state via `agent.aget_state({"configurable": {"thread_id": thread_id}})`
3. Map LangGraph messages to user-facing `{role, content}` pairs
4. Exclude assistant messages that only contain tool calls or internal drafts matching runner sanitizer rules
5. Return messages in chronological order

#### Scenario: User and assistant messages returned
- **GIVEN** checkpoint state with at least one user message and one final assistant reply
- **WHEN** `GET /chat/threads/{thread_id}/messages` is called
- **THEN** the response includes both roles with text content

#### Scenario: Market thread rejected
- **WHEN** `thread_id` is `market:US:PRE_OPEN:2026-06-10`
- **THEN** the endpoint returns 400

#### Scenario: Empty thread returns empty list
- **GIVEN** a UUID with no checkpoint state
- **WHEN** history is requested
- **THEN** the response is `[]` (or 404 if coordinated with API metadata — MUST be consistent in implementation)

### Requirement: History mapping module
Message extraction logic MUST live in a dedicated module (e.g. `nam_agentic/services/checkpoint_messages.py`) covered by unit tests with fixture message lists.

#### Scenario: Tool-call-only assistant messages omitted
- **GIVEN** an assistant message whose content is empty and has tool calls
- **WHEN** mapping history for the API
- **THEN** that message is not included in the output
