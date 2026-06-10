## 1. Prompt & agent identity (do first)

- [x] 1.1 Rewrite `prompts/PORTFOLIO.md`: add **Direct user questions (chat)** vs **Scheduled portfolio cycle (events)** sections; news tool-first; market closed ≠ no news; answer latest message only
- [x] 1.2 Delete `prompts/CHAT.md`
- [x] 1.3 Simplify `portfolio_manager.py`: load `PORTFOLIO.md` only (remove CHAT concat)
- [x] 1.4 Remove `build_chat_message()`; keep `build_synthesis_nudge()` only; update chat router to pass raw `body.content`
- [x] 1.5 Update news tool docstrings (Yahoo: recent headlines anytime; Bourso: cache window)
- [x] 1.6 Update/remove `test_chat_prompt.py` for new module shape

## 2. Agentic — runner & stream protocol

- [x] 2.1 Implement turn-scoped final text selection (after latest human message of current turn)
- [x] 2.2 Add completeness checks (reject preamble-only / mid-sentence fragments) + synthesis nudge retry
- [x] 2.3 Add news-intent guardrail: nudge if no news tool called when question requires headlines
- [x] 2.4 Refactor streaming: live model tokens on final answer (`stream_mode=["messages"]` or equivalent); remove fake-stream-only path
- [x] 2.5 Add `thread_id` to every `ChatStreamEvent`; set at stream start in chat router
- [x] 2.6 Implement `checkpoint_messages.py` + unit tests
- [x] 2.7 Add `GET /chat/threads/{thread_id}/messages` on agentic
- [x] 2.8 Agentic tests: raw user message, turn-scoped answer, news-after-close scenario (mock tools)

## 3. Database — chat thread metadata

- [x] 3.1 Add `ChatThread` model in `packages/db/nam_db/models/chat_thread.py`
- [x] 3.2 Alembic migration (`chat_threads`, FK `user_id`, index `updated_at`)
- [x] 3.3 Export model per package convention

## 4. API — chat threads REST + proxy

- [x] 4.1 Pydantic schemas: `ChatThreadRead`, `ChatThreadCreate`, `ChatThreadUpdate`, `ChatMessageRead`
- [x] 4.2 `ChatThreadService` CRUD (singleton user)
- [x] 4.3 Routes: `GET/POST /chat/threads`, `PATCH/DELETE /chat/threads/{id}`
- [x] 4.4 Proxy `GET /chat/threads/{id}/messages` → agentic
- [x] 4.5 Upsert thread metadata after successful chat stream (title from first user message)
- [x] 4.6 Wire router in `nam_api/main.py`; API tests with mocked agentic
- [x] 4.7 Regenerate Orval client on front (manual `threadsApi.ts` until next `pnpm orval` with API up)

## 5. Front — conversation sidebar v2

- [x] 5.1 Extract chat types + stream reducer helper (`chatStream.ts` or equivalent)
- [x] 5.2 Refactor `ChatProvider`: `conversations` map, per-thread `isStreaming`, route by `event.thread_id`
- [x] 5.3 Add `ConversationSidebar` (list, new, delete, streaming dot)
- [x] 5.4 Update `/chat` layout: sidebar + `ChatView`
- [x] 5.5 Load history on conversation select; remove `sessionStorage` thread as source of truth
- [x] 5.6 Responsive sidebar CSS

## 6. Verification & docs

- [x] 6.1 Agentic test: simple chat turn does not call `write_todos`
- [x] 6.2 Agentic test: two-turn thread finalizes second turn only
- [ ] 6.3 Manual QA: news question with US market closed → tools called → full answer
- [ ] 6.4 Manual QA: multi-conv switch + reload + parallel streams
- [x] 6.5 Update `openspec.md` and `AGENTS.md` (single PM prompt, sidebar, thread = conv)
