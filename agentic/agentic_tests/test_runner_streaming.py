"""Deep Agents / LangGraph v2 streaming helpers."""

from langchain_core.messages import AIMessage, ToolMessage

from nam_agentic.runner import _coerce_updates_stream_part


def test_coerce_updates_stream_part_v2_dict() -> None:
    part = {
        "type": "updates",
        "ns": ("tools:call_abc",),
        "data": {"model_request": {"messages": []}},
    }
    ns, data = _coerce_updates_stream_part(part) or ((), {})
    assert ns == ("tools:call_abc",)
    assert "model_request" in data


def test_coerce_updates_stream_part_legacy_tuple() -> None:
    part = ("updates", {"tools": {"messages": []}})
    ns, data = _coerce_updates_stream_part(part) or ((), {})
    assert ns == ()
    assert "tools" in data


def test_coerce_updates_stream_part_legacy_subgraph_tuple() -> None:
    part = (("tools:call_abc",), "updates", {"tools": {"messages": []}})
    ns, data = _coerce_updates_stream_part(part) or ((), {})
    assert ns == ("tools:call_abc",)


async def test_model_request_node_triggers_task_status() -> None:
    """model_request is the node name in LangGraph >= 1.1 / Deep Agents streaming doc."""
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4

    from nam_agentic.context import NamRuntimeContext
    from nam_agentic.enums import MarketPhase
    from nam_agentic.runner import AgentRunner

    factory = MagicMock()
    agent = MagicMock()
    factory.build.return_value = agent
    runner = AgentRunner(factory)
    question = "Analyse STM"

    async def fake_astream(*_args, **_kwargs):
        yield {
            "type": "updates",
            "ns": (),
            "data": {
                "model_request": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "task",
                                    "args": {
                                        "subagent_type": "sector-analyst",
                                        "description": "STM report",
                                    },
                                    "id": "call_1",
                                }
                            ],
                        )
                    ]
                }
            },
        }
        yield {
            "type": "updates",
            "ns": ("tools:call_1",),
            "data": {"model_request": {"messages": []}},
        }
        yield {
            "type": "updates",
            "ns": (),
            "data": {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content="Rapport STM détaillé." * 30,
                            tool_call_id="call_1",
                            name="task",
                        )
                    ]
                }
            },
        }
        yield {
            "type": "updates",
            "ns": (),
            "data": {
                "model_request": {
                    "messages": [
                        AIMessage(content="Synthèse STM complète pour l'utilisateur." * 50)
                    ]
                }
            },
        }

    agent.astream = fake_astream
    agent.aget_state = AsyncMock(
        return_value=MagicMock(
            values={
                "messages": [
                    __import__("langchain_core.messages", fromlist=["HumanMessage"]).HumanMessage(
                        content=question
                    ),
                    AIMessage(content="Synthèse STM complète pour l'utilisateur." * 50),
                ]
            }
        )
    )

    labels: list[str] = []
    async for event in runner.stream_events(
        question,
        context=NamRuntimeContext(user_id=uuid4(), phase=MarketPhase.CHAT, thread_id="t1"),
        user_question=question,
        thread_id="t1",
    ):
        if event.type == "status" and event.tool:
            labels.append(event.tool)

    assert any("sector" in label.lower() or "expert" in label.lower() for label in labels)
