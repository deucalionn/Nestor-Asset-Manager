## MODIFIED Requirements

### Requirement: Authenticated app layout with sidebar

After onboarding, app pages MUST use a persistent layout with a left sidebar and main content area.

#### Scenario: Sidebar navigation items

- **WHEN** the user views any post-onboarding page
- **THEN** a sidebar displays at least two items: Dashboard and Chat
- **AND** Dashboard links to `/dashboard`
- **AND** Chat links to `/chat` and is navigable (not disabled)

#### Scenario: Active route highlight

- **WHEN** the user is on `/dashboard`
- **THEN** the Dashboard nav item is highlighted using accent color `#68B3AE`

## ADDED Requirements

### Requirement: Chat page with WebSocket client
The front MUST expose `/chat` with a functional chat UI that connects to `{API_URL}/ws/chat` via WebSocket.

The page MUST:

- Send JSON messages `{ content, thread_id? }`
- Display streamed assistant tokens from `{ type: "token", content }` events
- Persist `thread_id` from `{ type: "done", thread_id }` in component state for follow-up messages
- Surface `{ type: "error", message }` to the user

#### Scenario: User sends first message
- **WHEN** the user submits a message on `/chat` with no prior `thread_id`
- **THEN** the client opens WebSocket to the API
- **AND** assistant response tokens appear incrementally
- **AND** `thread_id` is stored after the `done` event

#### Scenario: Follow-up message continues thread
- **GIVEN** a stored `thread_id` from a prior exchange
- **WHEN** the user sends another message
- **THEN** the outbound JSON includes that `thread_id`
- **AND** the assistant can reference prior conversation context (via agentic checkpointer)

#### Scenario: Chat uses API URL only
- **WHEN** the chat WebSocket connection is established
- **THEN** the host is `NEXT_PUBLIC_API_URL` (or equivalent)
- **AND** the client does not connect directly to nam-agentic port 8001
