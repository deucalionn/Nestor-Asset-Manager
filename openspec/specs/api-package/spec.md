## Requirements

### Requirement: FastAPI application skeleton
The `nam-api` package MUST expose a FastAPI application at `nam_api/main.py` with an `app` instance.

#### Scenario: Application import
- **WHEN** `from nam_api.main import app` is executed
- **THEN** a valid FastAPI instance is returned

### Requirement: Health endpoint
The API MUST expose `GET /health` returning `{"status": "ok"}`.

#### Scenario: Health check
- **WHEN** a client sends `GET /health`
- **THEN** the response status is 200
- **AND** the body contains `"status": "ok"`

### Requirement: Package layout
The `nam-api` package MUST follow this directory structure:

```text
api/
├── pyproject.toml
└── nam_api/
    ├── main.py
    ├── routers/
    ├── services/
    ├── schemas/
    └── websocket/
        └── chat.py   (live WS proxy → agentic /chat/stream)
```

#### Scenario: Module discoverability
- **WHEN** the package is installed
- **THEN** all listed directories exist with `__init__.py` files

### Requirement: Package dependencies
`nam-api` MUST declare a dependency on `nam-db` via uv path dependency.

`nam-api` MUST NOT declare a dependency on `nam-agentic` — coupling to the agent runtime is HTTP-only via `AGENTIC_URL`.

#### Scenario: Dependency resolution
- **WHEN** `uv sync` runs in the `api/` package context
- **THEN** `nam-db` is installed
- **AND** `nam-agentic` is absent from `nam-api` dependencies

### Requirement: Async-first
All route handlers and services MUST use `async def` — no synchronous SQLAlchemy sessions in the API layer.

#### Scenario: Async route handlers
- **WHEN** reviewing router files
- **THEN** all endpoint functions are declared `async def`

### Requirement: Pydantic schemas isolated
HTTP request/response schemas MUST live in `nam_api/schemas/` and import enums from `nam_db.enums`.

#### Scenario: No duplicate enums
- **WHEN** an API schema needs `Strategy`
- **THEN** it imports `Strategy` from `nam_db.enums` — never redefines it

### Requirement: WebSocket chat proxy
`nam_api/websocket/chat.py` MUST implement the live WebSocket chat proxy per `api-chat-proxy` spec.

The module MUST register `/ws/chat` and proxy streaming HTTP to `{AGENTIC_URL}/chat/stream`.

#### Scenario: Chat module functional
- **WHEN** `nam_api.main` is loaded
- **THEN** `/ws/chat` WebSocket route is registered
- **AND** `import nam_api.websocket.chat` does not raise

#### Scenario: No Python import of agentic
- **WHEN** `nam-api` package sources are reviewed
- **THEN** no `import nam_agentic` or `from nam_agentic` appears in `nam_api/`
