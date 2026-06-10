"""Map LangGraph checkpoint messages to user-visible chat history."""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from nam_agentic.services.chat_messages import human_message_text, message_text


def to_chat_history(messages: list[Any], *, limit: int = 100) -> list[dict[str, str]]:
    """Return chronological user/assistant messages for API display."""
    rows: list[dict[str, str]] = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            text = human_message_text(msg)
            if text:
                rows.append({"role": "user", "content": text})
        elif isinstance(msg, AIMessage) and not msg.tool_calls:
            text = message_text(msg)
            if text:
                rows.append({"role": "assistant", "content": text})
    if len(rows) > limit:
        return rows[-limit:]
    return rows
