"""Shared helpers for LangGraph message text extraction."""

import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

_TOOL_DUMP_MARKERS = (
    "YahooNewsItem(",
    "PositionItem(",
    "GetPortfolioPositionsOutput",
    "yahoo_symbol=",
    "resolved_from_db=",
)

_UUID_PATTERN = re.compile(
    r"UUID\(['\"][0-9a-f-]{36}['\"]\)|\b[0-9a-f]{8}-[0-9a-f-]{4}-[0-9a-f-]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_LATEX_TEXT_PATTERN = re.compile(r"\$\\text\{([^}]+)\}\$")
_LATEX_INLINE_PATTERN = re.compile(r"\$([^$\\]+)\$")
_PROSE_AFTER_DUMP = re.compile(
    r"(J'|J'ai|En |Voici|Bilan|Oui|Non,|Pour |Mon |Votre |Les |D'après|Ces |"
    r"Verdict|Résumé|Synthèse|Recommandation)",
)
# task() is synchronous — these claims are always false in NAM chat.
_ASYNC_SUBAGENT_WAIT = re.compile(
    r"(?is)"
    r"(en attente (de|du|d['\u2019])|waiting for (the |a )?(return|sub))"
    r"|(restitution du sous-agent|return of the sub-?agent)"
    r"|(je ne peux rien faire de plus tant que|cannot do anything more until)"
    r"|((travail|work) (est |is )?en cours|(work )?is in progress).{0,80}(sous-agent|sub-?agent)"
    r"|(please give me a moment|donnez-moi (un |l['\u2019])?instant)"
)
# Subagents have Yahoo price tools — these refusals are always false.
_MISSING_MARKET_DATA_ACCESS = re.compile(
    r"(?is)"
    r"(cannot provide (real-time|live) (prices|quotes|market))"
    r"|(je ne peux pas (vous )?fournir.{0,60}(prix|cours).{0,40}(temps réel|direct|instantané))"
    r"|(no real-time market data (api|access))"
    r"|(pas d['\u2019]api.{0,40}(marché|market|temps réel|cours))"
    r"|(données (de marché )?en temps réel.{0,40}(impossible|indisponible|limit|restreint))"
    r"|(limitations strictes de mes outils)"
    r"|(do not have access to real-time)"
    r"|(lack a real-time market data)"
    r"|(utiliser un outil de courtage standard pour le suivi des cours)"
)

MIN_POST_TASK_SYNTHESIS_CHARS = 600


def human_message_text(message: HumanMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts).strip()
    return str(content).strip() if content else ""


def message_text(message: AIMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                part_type = part.get("type")
                if part_type == "text":
                    text = part.get("text")
                    if isinstance(text, str):
                        parts.append(text)
        return "".join(parts).strip()
    return str(content).strip() if content else ""


def find_turn_start_index(messages: list[Any], user_question: str) -> int:
    question = user_question.strip()
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if isinstance(msg, HumanMessage):
            text = human_message_text(msg)
            if text == question or (question and question in text):
                return i
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            return i
    return max(len(messages) - 1, 0)


def _last_tool_index(messages: list[Any], *, tool_name: str | None = None) -> int:
    last = -1
    for i, msg in enumerate(messages):
        if not isinstance(msg, ToolMessage):
            continue
        if tool_name is None or getattr(msg, "name", None) == tool_name:
            last = i
    return last


def pick_turn_assistant_text(messages: list[Any], turn_start: int) -> str:
    """Last assistant message for the turn.

    When task() ran, only text **after the last task ToolMessage** counts — earlier
    "I am orchestrating…" stubs must not be returned as the final answer.
    """
    turn_messages = messages[turn_start + 1 :]
    if not turn_messages:
        return ""

    last_task_rel = _last_tool_index(turn_messages, tool_name="task")
    if last_task_rel >= 0:
        for msg in reversed(turn_messages[last_task_rel + 1 :]):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                text = message_text(msg)
                if text:
                    return text
        return ""

    last_tool_rel = _last_tool_index(turn_messages)
    search = turn_messages[last_tool_rel + 1 :] if last_tool_rel >= 0 else turn_messages

    for msg in reversed(search):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            text = message_text(msg)
            if text:
                return text

    if last_tool_rel >= 0:
        return ""

    for msg in reversed(turn_messages):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            text = message_text(msg)
            if text:
                return text
    return ""


def text_claims_async_subagent_wait(text: str) -> bool:
    """True when the PM tells the user it is waiting for a subagent (impossible here)."""
    return bool(text.strip() and _ASYNC_SUBAGENT_WAIT.search(text))


def text_claims_missing_market_data_access(text: str) -> bool:
    """True when the PM falsely claims it has no market/price API (subagents do)."""
    return bool(text.strip() and _MISSING_MARKET_DATA_ACCESS.search(text))


def task_tool_result_chars(messages: list[Any]) -> int:
    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage) or getattr(msg, "name", None) != "task":
            continue
        content = msg.content
        if isinstance(content, str):
            return len(content)
        return len(str(content)) if content is not None else 0
    return 0


def find_unsynthesized_task_index(
    messages: list[Any],
    *,
    min_synthesis_chars: int = MIN_POST_TASK_SYNTHESIS_CHARS,
) -> int | None:
    """Index of the last task ToolMessage not followed by a real user-facing synthesis."""
    last_task_idx: int | None = None
    for i, msg in enumerate(messages):
        if isinstance(msg, ToolMessage) and getattr(msg, "name", None) == "task":
            last_task_idx = i

    if last_task_idx is None:
        return None

    content = messages[last_task_idx].content
    if not isinstance(content, str) or len(content) < 200:
        return None

    for msg in messages[last_task_idx + 1 :]:
        if not isinstance(msg, AIMessage) or msg.tool_calls:
            continue
        text = message_text(msg)
        if len(text) >= min_synthesis_chars and not text_claims_async_subagent_wait(text):
            return None

    return last_task_idx


def sanitize_user_text(text: str | None, *, aggressive: bool = True) -> str | None:
    if not text:
        return None
    cleaned = text
    if aggressive and any(marker in text for marker in _TOOL_DUMP_MARKERS):
        match = _PROSE_AFTER_DUMP.search(text)
        if match and match.start() > 0:
            cleaned = text[match.start() :].lstrip() or text
    cleaned = _UUID_PATTERN.sub("", cleaned)
    cleaned = _LATEX_TEXT_PATTERN.sub(r"\1", cleaned)
    cleaned = _LATEX_INLINE_PATTERN.sub(r"\1", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() or None


def sanitize_stream_token(text: str | None, *, aggressive: bool = True) -> str | None:
    """Strip tool-dump prefixes from a token (legacy stream path; kept for tests)."""
    if not text:
        return None
    if not aggressive or not any(marker in text for marker in _TOOL_DUMP_MARKERS):
        return text
    return sanitize_user_text(text, aggressive=aggressive)
