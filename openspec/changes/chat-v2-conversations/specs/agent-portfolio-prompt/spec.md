## ADDED Requirements

### Requirement: Single Portfolio Manager system prompt
The compiled Deep Agent MUST use **one** system prompt sourced from `prompts/PORTFOLIO.md` via `PortfolioManagerAgent.system_prompt()`.

There MUST NOT be a separate chat system prompt file concatenated at runtime. `prompts/CHAT.md` MUST be removed.

#### Scenario: Factory builds graph with PORTFOLIO only
- **WHEN** `DeepAgentFactory.build()` runs at startup
- **THEN** `create_deep_agent(system_prompt=...)` receives `PORTFOLIO.md` content only
- **AND** no `CHAT.md` content is included

### Requirement: Trigger-based behavior in PORTFOLIO.md
`PORTFOLIO.md` MUST distinguish two interaction modes for the **same PM role**:

**Direct user questions (chat):**

- Answer the latest user message; prior thread context is background only
- Use tools proportionally; call news tools for headline / “what happened today” questions
- Market session closed MUST NOT be used as a reason to skip news retrieval
- MUST NOT invent unstated cash amounts or allocation tasks
- MUST NOT use `write_todos` or mandatory expert committee for simple factual or news Q&A

**Scheduled portfolio cycle (events):**

- Triggered by event seed messages (e.g. `market_session_seed_message`, onboarding seeds)
- Full committee workflow permitted: calendar refresh, `write_todos`, parallel `task()` delegation, optional `create_recommendation`

#### Scenario: Chat user question is passed raw
- **WHEN** `POST /chat/stream` receives `content="Quoi de neuf côté US aujourd'hui?"`
- **THEN** `AgentRunner` receives that string unchanged (no `[CHAT MODE]` prefix)
- **AND** the agent is expected to fetch news via tools before answering

#### Scenario: Market cron keeps committee workflow
- **WHEN** `market.session` invokes the agent with `market_session_seed_message`
- **THEN** the seed references the scheduled cycle workflow in `PORTFOLIO.md`
- **AND** `write_todos` and multi-expert delegation remain valid for that run

### Requirement: Remove chat message wrapper
`nam_agentic/services/chat_prompt.py` MUST NOT wrap user content in `[CHAT MODE]` or reference deleted prompt files.

`build_chat_message()` MUST be removed. A minimal `build_synthesis_nudge(user_question: str)` MAY remain for runner finalization.

#### Scenario: Chat router uses raw content
- **WHEN** the chat stream endpoint processes a request
- **THEN** `AgentRunner.stream_events(message=body.content, user_question=body.content, ...)`
- **AND** `body.content` appears verbatim in the LangGraph human message for that turn

### Requirement: Tool docstrings align with chat behavior
Market news tool descriptions MUST NOT imply that news is unavailable when a market is closed. Yahoo news tool MUST describe **recent headlines available anytime**.

#### Scenario: Bourso news tool remains cache-based
- **WHEN** the agent needs macro headlines outside market hours
- **THEN** `get_financials_news_from_bourso` docstring supports use with `since_hours` default (e.g. 48h)
- **AND** nothing in the docstring blocks off-hours use
