## MODIFIED Requirements

### Requirement: Package dependencies
`nam-api` MUST declare a dependency on `nam-db` via uv path dependency.

`nam-api` MUST NOT declare a dependency on `nam-agentic` — coupling to the agent runtime is HTTP-only via `AGENTIC_URL`.

#### Scenario: Dependency resolution
- **WHEN** `uv sync` runs in the `api/` package context
- **THEN** `nam-db` is installed
- **AND** `nam-agentic` is absent from `nam-api` dependencies

### Requirement: WebSocket chat stub
`nam_api/websocket/chat.py` MUST implement the live WebSocket chat proxy per `api-chat-proxy` spec.

The module MUST register `/ws/chat` and proxy streaming HTTP to `{AGENTIC_URL}/chat/stream`.

#### Scenario: Chat module functional
- **WHEN** `nam_api.main` is loaded
- **THEN** `/ws/chat` WebSocket route is registered
- **AND** `import nam_api.websocket.chat` does not raise

#### Scenario: No Python import of agentic
- **WHEN** `nam-api` package sources are reviewed
- **THEN** no `import nam_agentic` or `from nam_agentic` appears in `nam_api/`
