## 1. Checkpointer and dependencies

- [x] 1.1 Add `langgraph-checkpoint-postgres` (or project-standard async Postgres checkpointer) to `agentic/pyproject.toml`
- [x] 1.2 Add `database_url` to `nam_agentic/settings.py`; create checkpointer in lifespan; call `setup()`
- [x] 1.3 Build compiled graph in lifespan **before** `scheduler.start()`: checkpointer → `DeepAgentFactory.build()` → `app.state.agent_runner`
- [x] 1.4 Remove lazy `_resolve_runner()` / `runner_factory` pattern — inject lifespan `AgentRunner` into `EventHandler`
- [x] 1.5 Add agentic tests with mock checkpointer or test Postgres fixture

## 2. Shared backend `/user/` route

- [x] 2.1 Extend `build_agent_backend()` with `/user/` → `{agent_workspace_dir}/user` FilesystemBackend
- [x] 2.2 Ensure `EventHandler` creates `{workspace}/user/{user_id}/` on profile events
- [x] 2.3 Update `PORTFOLIO.md` onboarding paths to `/user/{user_id}/USER_GOALS.md`
- [x] 2.4 Add test: write/read `/user/...` survives via backend fixture

## 3. Deep agent factory hardening

- [x] 3.1 Disable `general-purpose` subagent via harness profile in `factory.py`
- [x] 3.2 Wire `app.state.agent_runner` into `EventHandler` and `/chat/stream`; drop `@lru_cache` and `get_agent_runner()` lazy factory
- [x] 3.3 Update `AgentRunner` to pass `configurable.thread_id` on invoke/stream
- [x] 3.4 Implement market-session `thread_id` as `market:{market}:{phase}:{date}`

## 4. Profile event wiring

- [x] 4.1 Implement `_on_user_profile_created` → `AgentRunner.invoke()` with onboarding seed
- [x] 4.2 Implement `_on_user_profile_updated` → `AgentRunner.invoke()` with refresh seed (rewrite `USER_GOALS.md`)
- [x] 4.3 Remove `CHAT_MESSAGE` from `EventType` and delete chat handler branch in `EventHandler`
- [x] 4.4 Add `test_event_handler.py` coverage for profile invoke (mock runner)

## 5. Agentic chat stream

- [x] 5.1 Add Pydantic schemas `ChatStreamRequest`, `ChatStreamEvent` in agentic
- [x] 5.2 Implement `POST /chat/stream` router with NDJSON streaming
- [x] 5.3 Wire route to shared `AgentRunner.stream()` with `MarketPhase.CHAT`
- [x] 5.4 Add agentic integration test with mock agent stream

## 6. API WebSocket proxy

- [x] 6.1 Verify `agentic_url` in `nam_api/settings.py`; document `AGENTIC_URL` in `.env.example` if missing
- [x] 6.2 Add `nam_api/schemas/chat.py` (client/server message types)
- [x] 6.3 Implement `websocket/chat.py` proxy: WS ↔ HTTP stream to `/chat/stream`
- [x] 6.4 Register WebSocket route in `main.py`
- [x] 6.5 Confirm `nam-api` has no `nam-agentic` Python path dependency (HTTP only)
- [x] 6.6 Add API tests with mocked httpx stream

## 7. Frontend chat

- [x] 7.1 Add `/chat` page with message list and input
- [x] 7.2 Implement WebSocket client to `{API_URL}/ws/chat`
- [x] 7.3 Enable Chat nav item (remove "coming soon")
- [x] 7.4 Store and reuse `thread_id` across messages

## 8. Infra and verification

- [x] 8.1 Update root `.env.example` with `AGENTIC_URL` (api) and checkpoint notes
- [x] 8.2 Document `agent_workspace` volume persistence in README or `.env.example`
- [x] 8.3 Update `openspec.md` chat flow (WS proxy → `/chat/stream`, not `chat.message` event)
- [x] 8.4 Run `just test` and `uv run pytest agentic/tests -q`
- [x] 8.5 Manual smoke: setup → onboarding file on volume; chat WS round-trip (automated WS→agentic integration test in `api/tests/api/test_chat_integration.py`; onboarding file still operator-verified after `POST /setup` + agent run)
