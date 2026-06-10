## MODIFIED Requirements

### Requirement: Phase-aware system prompt
**REMOVED** — superseded by single `PORTFOLIO.md` prompt with trigger-based sections. See `agent-portfolio-prompt` capability.

**Reason:** Chat and events share one PM role; behavior is driven by input (user question vs event seed), not by swapping system prompts or maintaining `CHAT.md`.

**Migration:** Delete `CHAT.md`; rewrite `PORTFOLIO.md`; remove `PortfolioManagerAgent` CHAT concatenation.

## ADDED Requirements

### Requirement: Single compiled graph for chat and events
`DeepAgentFactory` MUST compile **one** Deep Agent graph at startup used for chat streams, market events, and profile seeds.

There MUST NOT be a separate chat-only compiled graph or phase-specific system prompt switch.

#### Scenario: Chat and market session share one graph
- **WHEN** `AgentRunner.stream_events()` runs for chat and `AgentRunner.invoke()` runs for `market.session`
- **THEN** both use the same compiled graph instance
- **AND** the same `PORTFOLIO.md` system prompt

### Requirement: Checkpoint message mapper
`nam_agentic` MUST provide a tested module to map LangGraph checkpoint messages to API-safe chat history (shared by the history endpoint and runner tests).

#### Scenario: Mapper covered by unit tests
- **WHEN** agentic unit tests run
- **THEN** fixture message lists verify tool-call-only messages are filtered and order is chronological

### Requirement: Chat prompt module scope
`nam_agentic/services/chat_prompt.py` MUST contain only runner helpers (e.g. synthesis nudge). It MUST NOT define a second system prompt or user-message wrapper.

#### Scenario: No build_chat_message export
- **WHEN** the chat router imports from `chat_prompt`
- **THEN** only synthesis/finalization helpers are imported
- **AND** `build_chat_message` is not present in the codebase
