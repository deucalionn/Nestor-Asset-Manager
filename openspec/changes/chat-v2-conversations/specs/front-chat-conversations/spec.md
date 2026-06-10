## ADDED Requirements

### Requirement: Conversation sidebar on chat page
The `/chat` page MUST render a two-column layout:

- **Left:** conversation list sidebar (~240–280px)
- **Right:** active conversation messages and composer

The sidebar MUST display:

- A **New conversation** control
- A scrollable list of conversations (title + relative `updated_at`)
- A visual indicator on threads with an in-progress stream

#### Scenario: User creates a new conversation
- **WHEN** the user clicks **New conversation**
- **THEN** a new `thread_id` is allocated via `POST /chat/threads`
- **AND** the message pane clears
- **AND** the new thread is selected in the sidebar

#### Scenario: User switches conversation
- **GIVEN** at least two conversations exist
- **WHEN** the user selects another thread in the sidebar
- **THEN** the message pane loads that thread's history via `GET /chat/threads/{id}/messages`
- **AND** subsequent sends include that `thread_id`

### Requirement: Multi-thread ChatProvider state
`ChatProvider` MUST maintain per-thread state keyed by `thread_id`:

- `messages`, `isStreaming`, `activityStatus`, `error`
- One shared WebSocket at app layout level
- Route inbound stream events using `thread_id` on **every** event (token, status, done, error)

`isStreaming` MUST be tracked **per thread**, not globally — the user MAY send a message on thread B while thread A is still streaming.

#### Scenario: Background stream while on another thread
- **GIVEN** thread A is streaming a response
- **WHEN** the user switches to thread B and sends a new message
- **THEN** thread A continues receiving tokens in provider state
- **AND** thread B can stream independently
- **AND** the sidebar shows streaming indicators on both threads as applicable

#### Scenario: Events routed by thread_id
- **WHEN** a `token` event arrives with `thread_id=T`
- **THEN** the front appends content to conversation `T` regardless of which conversation is currently selected

### Requirement: Conversation list synced with API
On chat page mount, the front MUST fetch `GET /chat/threads` and populate the sidebar. Creating, renaming, or deleting conversations MUST call the corresponding REST endpoints.

The front MUST NOT use a single `sessionStorage` thread key as the source of truth.

#### Scenario: Conversations survive page reload
- **GIVEN** multiple conversations exist in `chat_threads`
- **WHEN** the user reloads `/chat`
- **THEN** the sidebar lists those conversations
- **AND** selecting one loads history from the API

### Requirement: Orval-generated API client
Chat thread REST endpoints MUST be consumed via the generated API client under `front/src/api/generated/`.

#### Scenario: Type-safe thread list
- **WHEN** the chat UI fetches threads
- **THEN** it uses generated types for `ChatThreadRead` and mutations

### Requirement: ChatProvider module structure
Chat state logic MUST live in focused modules under `front/src/components/chat/` or `front/src/lib/chat/` (provider, types, stream reducer). Presentation components (`ChatView`, `ConversationSidebar`) MUST NOT embed WebSocket protocol parsing inline beyond thin hooks.

#### Scenario: Separation of concerns
- **WHEN** reviewing the front chat code
- **THEN** WebSocket event handling is centralized in the provider or a dedicated `chatStream.ts` helper
- **AND** UI components consume `useChat()` only
