## ADDED Requirements

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
        └── chat.py   (stub)
```

#### Scenario: Module discoverability
- **WHEN** the package is installed
- **THEN** all listed directories exist with `__init__.py` files

### Requirement: Package dependencies
`nam-api` MUST declare dependencies on `nam-db` and `nam-agentic` via uv path dependency.

#### Scenario: Dependency resolution
- **WHEN** `uv sync` runs in the `api/` package context
- **THEN** both `nam-db` and `nam-agentic` are installed

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

### Requirement: WebSocket chat stub
`nam_api/websocket/chat.py` MUST exist as a stub module with a documented placeholder for future Deep Agent streaming integration.

#### Scenario: Chat module present
- **WHEN** `import nam_api.websocket.chat` is executed
- **THEN** the module loads without error
