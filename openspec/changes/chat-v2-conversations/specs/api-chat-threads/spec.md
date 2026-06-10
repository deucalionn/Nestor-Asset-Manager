## ADDED Requirements

### Requirement: List chat threads
`nam-api` MUST expose `GET /chat/threads` returning threads for the singleton user ordered by `updated_at` descending.

Response item schema **ChatThreadRead**:

| Field | Type |
|-------|------|
| `id` | UUID |
| `title` | str |
| `created_at` | datetime |
| `updated_at` | datetime |

#### Scenario: Empty list for new user
- **WHEN** the user has no chat threads
- **THEN** `GET /chat/threads` returns `[]`

#### Scenario: Sorted by recent activity
- **GIVEN** two threads with different `updated_at`
- **WHEN** listing threads
- **THEN** the most recently updated thread appears first

### Requirement: Create chat thread
`nam-api` MUST expose `POST /chat/threads` accepting optional **ChatThreadCreate**:

| Field | Type | Constraints |
|-------|------|-------------|
| `title` | str \| None | max 120; server may default to `"New conversation"` |

The server MUST generate a new UUID for `id`.

#### Scenario: New thread returns id
- **WHEN** `POST /chat/threads` succeeds
- **THEN** response includes a new UUID `id`
- **AND** a `chat_threads` row is persisted

### Requirement: Update and delete chat thread
`nam-api` MUST expose:

- `PATCH /chat/threads/{thread_id}` with **ChatThreadUpdate** (`title` str, max 120)
- `DELETE /chat/threads/{thread_id}` → 204

#### Scenario: Rename conversation
- **WHEN** `PATCH` sets `title` to `"US market news"`
- **THEN** subsequent `GET /chat/threads` returns the updated title

#### Scenario: Delete removes from list
- **WHEN** `DELETE /chat/threads/{thread_id}` succeeds
- **THEN** the thread no longer appears in `GET /chat/threads`

### Requirement: Proxy message history
`nam-api` MUST expose `GET /chat/threads/{thread_id}/messages` proxying to agentic.

Query param: `limit` int (default 100, max 200).

Response: list of **ChatMessageRead**:

| Field | Type |
|-------|------|
| `role` | `"user"` \| `"assistant"` |
| `content` | str |

Internal/tool messages MUST NOT be exposed.

#### Scenario: History loaded for existing thread
- **GIVEN** a thread with prior user and assistant messages in the checkpoint
- **WHEN** the client calls `GET /chat/threads/{thread_id}/messages`
- **THEN** user-visible messages are returned in chronological order

#### Scenario: Unknown thread returns 404
- **WHEN** `thread_id` has no metadata row and no checkpoint state
- **THEN** the API returns 404

### Requirement: Thread metadata updated after chat turn
After a successful `/chat/stream` proxied through the WebSocket, nam-api (or agentic callback — implementation choice) MUST upsert `chat_threads.updated_at` and set `title` from the first user message when `title` is still the default placeholder.

#### Scenario: Title auto-set on first exchange
- **GIVEN** a thread titled `"New conversation"`
- **WHEN** the user sends `"Is the US market open?"`
- **AND** the stream completes with `done`
- **THEN** `title` becomes a truncated form of that question
