## Why

Chat v1 has a working WebSocket path and LangGraph checkpointer, but **quality is unacceptable**: answers truncate mid-sentence, the agent argues instead of calling tools (e.g. refuses US news because the market is “closed”), reopens stale topics, and treats every user message like a full market cron cycle. The front also supports only **one implicit conversation** (`sessionStorage` + in-memory messages).

Chat v2 fixes the **agent loop and prompts** (one PM role, proportional behavior), adds **multi-conversation UX** (sidebar, one conv = one `thread_id`), and delivers **clean, testable code** — no parallel prompt hacks.

## What Changes

- **Remove `CHAT.md` and `[CHAT MODE]` message wrapping** — one system prompt (`PORTFOLIO.md`), same Portfolio Manager whether triggered by user chat or scheduler event; behavior scales with the **input** (direct question vs cycle seed), not a second persona
- **Rewrite `PORTFOLIO.md`** — separate “direct user questions” from “scheduled portfolio cycle”; tool-first rules for news (market closed is irrelevant); answer the latest user message only
- **Rewrite `AgentRunner.stream_events`** — turn-scoped final text, live model token streaming, completeness guardrails, optional tool-missing nudge for news questions
- **`thread_id` on every stream event** — front can route multi-conversation streams on one WebSocket
- Add **`chat_threads`** table + REST API + checkpoint history endpoint
- **Front v2** — conversation sidebar, per-thread state, history reload from API
- Delete dead code: `chat_prompt.build_chat_message`, `prompts/CHAT.md`, CHAT+PORTFOLIO concatenation

## Capabilities

### New Capabilities

- `chat-threads-schema`: `ChatThread` model + Alembic migration
- `api-chat-threads`: REST CRUD + history proxy
- `agent-chat-history`: checkpoint → user-visible messages
- `front-chat-conversations`: sidebar + multi-thread `ChatProvider`
- `agent-portfolio-prompt`: single PM prompt, trigger-based workflow, removal of CHAT.md

### Modified Capabilities

- `agent-chat-stream`: turn-scoped streaming, `thread_id` on all events, raw user content, runner guardrails
- `agentic-package`: single compiled graph + one system prompt; delete CHAT prompt path
- `api-chat-proxy`: relay `thread_id` on every streamed event verbatim
- `front-app-shell`: chat layout with conversation sidebar

## Impact

- **packages/db/**: `chat_threads` migration
- **agentic/**: `runner.py`, `routers/chat.py`, `portfolio_manager.py`, `prompts/PORTFOLIO.md`; **delete** `CHAT.md`, slim `chat_prompt.py` (synthesis nudge only)
- **api/**: chat threads router; relay `thread_id` on stream events
- **front/**: `ChatProvider`, `ConversationSidebar`, Orval regen
- **tests:** runner turn-scope, news-without-tools nudge, thread CRUD, prompt regression (no dual-prompt)
