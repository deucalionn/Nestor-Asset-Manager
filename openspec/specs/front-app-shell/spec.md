## Requirements

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

### Requirement: Visual design system

The UI MUST follow a minimal, Stripe-inspired aesthetic with the NAM palette.

#### Scenario: Color palette

- **WHEN** rendering app chrome and primary actions
- **THEN** background is white (`#FFFFFF`)
- **AND** primary accent is `#68B3AE` (buttons, active nav, links)
- **AND** text uses high-contrast dark gray on white

#### Scenario: Layout spacing

- **WHEN** displaying dashboard content
- **THEN** content uses generous padding, subtle borders between sections, and card-style grouping
- **AND** avoids heavy shadows or cluttered dense tables

### Requirement: Route structure

The front MUST expose these routes in v1:

| Route | Purpose |
|-------|---------|
| `/onboarding` | First-run wizard |
| `/dashboard` | Portfolio home |
| `/chat` | Nestor chat (WebSocket via API) |
| `/` | Redirect to `/dashboard` or `/onboarding` based on profile |

#### Scenario: Root redirect

- **WHEN** the user visits `/`
- **THEN** they are redirected based on profile existence (same logic as onboarding guard)

### Requirement: Chat page with WebSocket client
The front MUST expose `/chat` with a functional chat UI that connects to `{NEXT_PUBLIC_API_URL}/ws/chat` via WebSocket.

The page MUST:

- Send JSON messages `{ content, thread_id? }`
- Display streamed assistant tokens from `{ type: "token", content }` events
- MAY display `{ type: "status" }` progress while waiting for tokens
- Persist `thread_id` from `{ type: "done", thread_id }` (e.g. `sessionStorage`) for follow-up messages
- Surface `{ type: "error", message }` to the user

#### Scenario: User sends first message
- **WHEN** the user submits a message on `/chat` with no prior `thread_id`
- **THEN** the client uses the WebSocket to the API
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
