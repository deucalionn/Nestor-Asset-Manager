## MODIFIED Requirements

### Requirement: ChatStreamRequest schema
`nam_agentic` MUST define Pydantic schemas for the chat stream API:

**ChatStreamRequest**:

| Field | Type | Constraints |
|-------|------|-------------|
| `content` | str | min 1, max 16000 |
| `thread_id` | str \| None | optional; server generates UUID if omitted |
| `user_id` | UUID \| None | optional; defaults to `settings.default_user_id` |

**ChatStreamEvent** (each streamed line):

| Field | Type | Notes |
|-------|------|-------|
| `type` | literal | `token`, `status`, `done`, `error` |
| `content` | str \| None | token text when `type=token` |
| `status` | literal \| None | `thinking`, `tool`, `writing` when `type=status` |
| `tool` | str \| None | human label when `type=status` and `status=tool` |
| `thread_id` | str | **required** on every event for the active stream |
| `message` | str \| None | error detail when `type=error` |

`status` events are UX progress signals relayed by the API proxy; the front MAY display them while waiting for tokens.

#### Scenario: New thread receives id on completion
- **WHEN** `POST /chat/stream` is called without `thread_id`
- **THEN** the server allocates a UUID at stream start
- **AND** every streamed event includes that `thread_id`
- **AND** the stream ends with `type=done` carrying the same `thread_id`

#### Scenario: Token events carry thread_id during stream
- **WHEN** the agent emits `type=token` events
- **THEN** each event includes `thread_id` matching the request thread
- **AND** the front can route tokens to the correct conversation without waiting for `done`

## ADDED Requirements

### Requirement: Raw user content to the graph
`/chat/stream` MUST pass the request `content` field to `AgentRunner` **without** prepending mode tags or secondary prompt references.

#### Scenario: No CHAT MODE wrapper
- **WHEN** the user sends `"Le marché US est-il ouvert?"`
- **THEN** the human message appended to the LangGraph state equals that string
- **AND** does not contain `[CHAT MODE]`

### Requirement: Turn-scoped final answer selection
`AgentRunner.stream_events()` MUST select the user-facing answer from assistant messages **after the latest human message of the current turn** only (matching `user_question`). It MUST NOT select assistant text from earlier turns.

If no qualifying assistant text exists after tool rounds, the runner MUST issue at most one synthesis nudge and re-evaluate within the same turn scope.

#### Scenario: Follow-up question does not replay old synthesis
- **GIVEN** a thread where a prior turn produced a long allocation synthesis
- **WHEN** the user asks a new factual question on the same thread
- **THEN** the streamed answer addresses the new question only

#### Scenario: Partial preamble not returned as final answer
- **GIVEN** the model emitted a short disclaimer before tool calls in the current turn
- **WHEN** a complete assistant answer exists later in the same turn
- **THEN** the final streamed text is the complete answer

### Requirement: Live token streaming on final answer
During final assistant generation, the runner MUST emit `token` events from model output as produced. The runner MUST NOT rely solely on post-hoc chunking of a post-selected blob.

Tool execution phases MAY emit only `status` events.

#### Scenario: User sees progressive text
- **WHEN** the agent produces a multi-sentence final answer
- **THEN** the client receives multiple `token` events before `done`
- **AND** concatenated tokens equal the full answer

### Requirement: Complete answer before terminal done
The runner MUST NOT emit `done` with an empty, truncated, or preamble-only answer. If synthesis nudge fails, emit `error` or an explicit fallback — not a mid-sentence fragment.

#### Scenario: Non-empty answer on success
- **WHEN** a chat turn completes successfully
- **THEN** concatenated token content is substantive (not a lone disclaimer)
- **OR** the stream ends with `type=error`

### Requirement: News questions require news tools
When the user question is classified as news/macro headline intent (implementation: keyword/heuristic or prompt compliance checked by runner), the turn MUST call at least one of `get_financials_news_from_bourso` or `get_asset_news_from_yf` before a final answer is streamed.

If the graph completes without such a call, the runner MUST issue one synthesis nudge instructing the agent to fetch news tools, then re-finalize.

#### Scenario: US market news after close
- **WHEN** the user asks for US market news from today while the US session is closed
- **THEN** the agent calls a news tool
- **AND** the final answer summarizes retrieved headlines
- **AND** does not claim tools cannot fetch news because the market is closed

### Requirement: Direct user questions skip committee machinery
For chat streams (`MarketPhase.CHAT`), a turn triggered by a direct user question MUST NOT require `write_todos` or mandatory multi-expert `task()` delegation for simple factual or news questions.

#### Scenario: Market hours question
- **WHEN** the user asks whether a market session is open
- **THEN** the agent does not call `write_todos` during that turn
- **AND** the final answer is direct and complete
