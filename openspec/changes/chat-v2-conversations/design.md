## Context

**Principle (product):** Nestor is always the **Portfolio Manager (CIO)**. Chat is the PM answering a user question. Events are the PM running a scheduled cycle. **Same role, same tools, same graph** — only the trigger message and `thread_id` differ.

**What went wrong in v1:**

| Symptom | Root cause |
|---------|------------|
| Truncated answers (`…lorsqu`) | Runner picks wrong/incomplete assistant blob after graph; fake token chunking |
| Refuses news when market closed | LLM confabulation; no tool call; `PORTFOLIO.md` “noise” + misread “live” tool docs |
| 300€ / hors-sujet | Thread history + `PORTFOLIO.md` §3 treats **every user message** like a full investment committee |
| `CHAT.md` ineffective | Dual prompts fight each other; `[CHAT MODE]` wrapper adds noise; override line ignored |

**Rejected approach:** Keep or strengthen `CHAT.md` as a chat-only persona. **Removed from scope.**

```
                    ┌─────────────────────────┐
                    │   Portfolio Manager     │
                    │   prompts/PORTFOLIO.md  │
                    │   (single system prompt)│
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              ▼                                     ▼
     User message (chat)                   Event seed (cron)
     "Quoi de neuf côté US?"              "Run EU PRE_OPEN cycle…"
              │                                     │
              ▼                                     ▼
     Direct-question rules                  Full cycle rules
     (answer question, tools as needed)     (write_todos, committee OK)
```

## Goals / Non-Goals

**Goals:**

- One conversation = one UUID `thread_id`; sidebar list; reload history after refresh
- Complete answers for the **current turn only**
- News / “what happened today” → **must fetch** via news tools; market session closed is **not** a blocker
- Clean codebase: no `CHAT.md`, no `[CHAT MODE]`, raw user content to the graph
- `thread_id` on **every** `ChatStreamEvent` for multi-conv routing
- Per-thread `isStreaming` (not global lock)

**Non-Goals:**

- Second compiled graph or phase-specific system prompts
- Multi-user auth
- Message edit/regenerate
- Checkpoint hard-delete on conversation delete (v2: metadata only)

## Decisions

### 1. Single prompt — rewrite PORTFOLIO.md, delete CHAT.md

`PORTFOLIO.md` gains an explicit section **“Direct user questions (chat)”**:

- Answer the **latest user message**; do not reopen prior topics unless referenced
- Do not invent unstated amounts or allocation tasks
- **Proportional depth:** simple factual → calendar/tools, short answer; news → `get_financials_news_from_bourso` / `get_asset_news_from_yf` **before** answering; allocation → context + optional experts
- **Market closed ≠ news unavailable** — headlines and cached Bourso items are always valid
- No `write_todos` for straightforward Q&A; no mandatory expert committee unless the question warrants it

Section **“Scheduled portfolio cycle (events)”** keeps the existing committee workflow for seeds like `market_session_seed_message()`.

`PortfolioManagerAgent.system_prompt()` loads **`PORTFOLIO.md` only**.

Chat router passes **`body.content` unchanged** to `AgentRunner` (no `build_chat_message` wrapper).

### 2. Runner rewrite

**Turn-scoped selection:**

1. After graph step(s), load checkpoint messages
2. Find the **latest human message** matching this turn’s raw `user_question`
3. Take the **last** substantive assistant message **after** that index (no `tool_calls`)
4. Reject incomplete text (mid-sentence, disclaimer-only, plan preamble) → synthesis nudge once → retry selection

**Tool guardrail (news class):** If the user question is news/macro (“what’s new”, “actu”, “headlines”, market region + today) and the turn completed with **zero** calls to `get_financials_news_from_bourso` or `get_asset_news_from_yf`, inject a synthesis nudge: *fetch news tools then answer*.

**Live streaming:** Emit `token` events from model stream on the final assistant generation (`stream_mode=["messages"]` or equivalent), not post-hoc `_chunk_for_stream` only.

**Delete:** fake-stream-only path as sole output mechanism.

### 3. Stream protocol — `thread_id` everywhere

Extend `ChatStreamEvent`:

| Field | Notes |
|-------|-------|
| `thread_id` | Present on **token**, **status**, **done**, **error** for the active stream |

Agentic sets `thread_id` at stream start (known from request). API proxy relays verbatim. Front routes events to `conversations[thread_id]`.

**Parallel sends:** Per-thread `isStreaming`; user may switch sidebar while another thread streams; client tracks outbound `thread_id` per send.

### 4. Two-layer persistence (unchanged)

| Layer | Store |
|-------|-------|
| Index | `chat_threads` (title, dates) |
| Memory | LangGraph checkpoint |

History: agentic `GET /chat/threads/{id}/messages` → API proxy → front on conversation select.

### 5. Front layout

```
/chat
├── ConversationSidebar (POST /chat/threads, list, delete)
└── ChatView (messages, composer)
```

`ChatProvider`: `Record<threadId, ConversationState>`, shared WS, route by `event.thread_id`.

### 6. Code hygiene

| Remove | Replace with |
|--------|----------------|
| `prompts/CHAT.md` | PORTFOLIO.md § direct questions |
| `build_chat_message()` | Raw `content` in chat router |
| CHAT+PORTFOLIO concat | `load("PORTFOLIO")` only |
| `sessionStorage` single thread | API `chat_threads` |
| Global `isStreaming` | Per-thread flag |

Keep `build_synthesis_nudge()` — rename/reword to reference user question only (no CHAT.md).

Update tool docstrings: Yahoo news = “recent headlines (available anytime)”, not “only when market open”.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| PORTFOLIO.md still too heavy | Code review + agentic tests assert no `write_todos` on simple chat turns |
| Model still skips tools | Runner news guardrail + synthesis nudge |
| WS event interleaving | `thread_id` on every event |
| Checkpoint orphans on delete | Document; defer hard delete |

## Migration Plan

1. Agentic: PORTFOLIO rewrite + runner + delete CHAT.md (immediate quality)
2. DB + API threads + history
3. Front sidebar + ChatProvider refactor
4. Drop legacy `sessionStorage` thread key

## Open Questions

- Hard-delete checkpoints on thread delete → **defer**
- LLM-generated conversation titles → **defer** (truncate first user message)
