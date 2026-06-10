"""AgentRunner stream behaviour with a mocked compiled agent."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from nam_agentic.context import NamRuntimeContext
from nam_agentic.enums import MarketPhase
from nam_agentic.runner import AgentRunner


def _make_runner() -> tuple[AgentRunner, MagicMock]:
    factory = MagicMock()
    agent = MagicMock()
    factory.build.return_value = agent
    return AgentRunner(factory), agent


def _chat_context(*, thread_id: str = "thread-1") -> NamRuntimeContext:
    return NamRuntimeContext(user_id=uuid4(), phase=MarketPhase.CHAT, thread_id=thread_id)


async def _collect_tokens(runner: AgentRunner, question: str) -> str:
    parts: list[str] = []
    async for event in runner.stream_events(
        question,
        context=_chat_context(),
        user_question=question,
        thread_id="thread-1",
    ):
        if event.type == "token" and event.content:
            parts.append(event.content)
    return "".join(parts)


@pytest.mark.asyncio
async def test_simple_chat_turn_does_not_call_write_todos() -> None:
    runner, agent = _make_runner()
    question = "How is my portfolio diversified?"

    async def fake_astream(*_args, **_kwargs):
        yield (
            "updates",
            {
                "model": {
                    "messages": [
                        AIMessage(
                            content="Your portfolio is well diversified across sectors.",
                            tool_calls=[],
                        )
                    ]
                }
            },
        )

    agent.astream = fake_astream
    agent.aget_state = AsyncMock(
        return_value=MagicMock(
            values={
                "messages": [
                    HumanMessage(content=question),
                    AIMessage(content="Your portfolio is well diversified across sectors."),
                ]
            }
        )
    )

    tool_labels: list[str] = []
    async for event in runner.stream_events(
        question,
        context=_chat_context(),
        user_question=question,
        thread_id="thread-1",
    ):
        if event.type == "status" and event.tool:
            tool_labels.append(event.tool)

    assert not any("write_todos" in label.lower() for label in tool_labels)
    assert not any("planification" in label.lower() for label in tool_labels)


@pytest.mark.asyncio
async def test_two_turn_thread_finalizes_second_turn_only() -> None:
    runner, agent = _make_runner()
    question = "Is the US market open?"

    async def fake_astream(*_args, **_kwargs):
        yield (
            "updates",
            {
                "model": {
                    "messages": [
                        AIMessage(content="No, the US market is currently closed.", tool_calls=[])
                    ]
                }
            },
        )

    agent.astream = fake_astream
    agent.aget_state = AsyncMock(
        return_value=MagicMock(
            values={
                "messages": [
                    HumanMessage(content="Old question"),
                    AIMessage(content="Old long allocation synthesis about 300 euros."),
                    HumanMessage(content=question),
                    AIMessage(content="No, the US market is currently closed."),
                ]
            }
        )
    )

    response = await _collect_tokens(runner, question)
    assert "300 euros" not in response
    assert "closed" in response.lower()

