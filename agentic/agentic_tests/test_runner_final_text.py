from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from nam_agentic.services.chat_messages import pick_turn_assistant_text
from nam_agentic.services.checkpoint_messages import to_chat_history


def test_pick_turn_assistant_text_uses_current_turn_only() -> None:
    messages = [
        HumanMessage(content="Old question"),
        AIMessage(content="Old long allocation synthesis about 300 euros."),
        HumanMessage(content="Le marché US est-il ouvert?"),
        AIMessage(content="Non, le marché US est actuellement fermé."),
    ]
    turn_start = 2
    assert pick_turn_assistant_text(messages, turn_start) == "Non, le marché US est actuellement fermé."


def test_pick_turn_assistant_text_prefers_post_task_synthesis() -> None:
    messages = [
        HumanMessage(content="Où placer 500€ en semi ?"),
        AIMessage(content="J'attends le retour du sector-analyst pour synthétiser."),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "task",
                    "args": {"subagent_type": "sector-analyst", "description": "x"},
                    "id": "1",
                }
            ],
        ),
        ToolMessage(content="Les semi surperforment le NASDAQ sur 12 mois.", tool_call_id="1", name="task"),
        AIMessage(content="Les semi-conducteurs surperforment le NASDAQ sur 12 mois."),
    ]
    assert (
        pick_turn_assistant_text(messages, 0)
        == "Les semi-conducteurs surperforment le NASDAQ sur 12 mois."
    )


def test_pick_turn_assistant_text_ignores_pre_task_stall_when_tools_present() -> None:
    messages = [
        HumanMessage(content="Où placer 500€ ?"),
        AIMessage(content="J'attends le sector-analyst."),
        AIMessage(
            content="",
            tool_calls=[{"name": "task", "args": {}, "id": "1"}],
        ),
        ToolMessage(content="Analyse sectorielle complète.", tool_call_id="1", name="task"),
    ]
    assert pick_turn_assistant_text(messages, 0) == ""


def test_pick_turn_assistant_text_ignores_post_task_wait_stub() -> None:
    messages = [
        HumanMessage(content="Analyse STMicroelectronics"),
        AIMessage(content="I am orchestrating the full analysis now."),
        AIMessage(
            content="",
            tool_calls=[{"name": "task", "args": {}, "id": "1"}],
        ),
        ToolMessage(content="STM: CA 17B$, marges en reprise…" * 50, tool_call_id="1", name="task"),
        AIMessage(
            content=(
                "I am orchestrating the full analysis now. Please give me a moment "
                "while I compile the comprehensive report."
            )
        ),
    ]
    picked = pick_turn_assistant_text(messages, 0)
    assert "Please give me a moment" in picked


def test_pick_turn_assistant_text_uses_task_not_later_write_todos() -> None:
    messages = [
        HumanMessage(content="Analyse STM"),
        AIMessage(content="", tool_calls=[{"name": "task", "args": {}, "id": "1"}]),
        ToolMessage(content="Rapport sectoriel détaillé.", tool_call_id="1", name="task"),
        AIMessage(content="", tool_calls=[{"name": "write_todos", "args": {}, "id": "2"}]),
        ToolMessage(content="ok", tool_call_id="2", name="write_todos"),
        AIMessage(content="STMicroelectronics est un leader des semi-conducteurs."),
    ]
    assert (
        pick_turn_assistant_text(messages, 0)
        == "STMicroelectronics est un leader des semi-conducteurs."
    )


def test_to_chat_history_filters_tool_only_messages() -> None:
    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="", tool_calls=[{"name": "get_user_context", "args": {}, "id": "1"}]),
        AIMessage(content="Final answer here."),
    ]
    rows = to_chat_history(messages)
    assert rows == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Final answer here."},
    ]
