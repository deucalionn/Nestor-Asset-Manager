## MODIFIED Requirements

### Requirement: Chat page with WebSocket client
The front MUST expose `/chat` with a functional chat UI that connects to `{NEXT_PUBLIC_API_URL}/ws/chat` via WebSocket.

The page MUST:

- Send JSON messages `{ content, thread_id? }`
- Display streamed assistant tokens from `{ type: "token", content }` events
- Display `{ type: "status" }` progress while waiting for tokens
- Manage multiple conversations via REST (`GET/POST/PATCH/DELETE /chat/threads`) and per-thread `thread_id`
- Load prior messages via `GET /chat/threads/{thread_id}/messages` when switching conversations
- Surface `{ type: "error", message }` to the user

The WebSocket connection SHOULD be established at app layout level (not only when `/chat` mounts) so streaming continues when navigating to other app routes.

#### Scenario: User sends first message in a new conversation
- **WHEN** the user submits a message in a newly created conversation
- **THEN** the client sends over the app WebSocket with that conversation's `thread_id`
- **AND** assistant response tokens appear incrementally
- **AND** the conversation list updates `updated_at` after `done`

#### Scenario: Follow-up message continues thread
- **GIVEN** a selected conversation with prior messages loaded
- **WHEN** the user sends another message
- **THEN** the outbound JSON includes that conversation's `thread_id`
- **AND** the assistant can reference prior context from the same thread only

#### Scenario: Chat uses API URL only
- **WHEN** the chat WebSocket connection is established
- **THEN** the host is `NEXT_PUBLIC_API_URL` (or equivalent)
- **AND** the client does not connect directly to nam-agentic port 8001

#### Scenario: Conversation sidebar visible on chat page
- **WHEN** the user navigates to `/chat`
- **THEN** a conversation list is visible alongside the message pane
- **AND** the user can switch between conversations without losing other in-flight streams
