import logging
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage

from nam_agentic.context import NamRuntimeContext
from nam_agentic.factory import CompiledDeepAgent, DeepAgentFactory
from nam_agentic.schemas.chat import ChatStreamEvent
from nam_agentic.services.chat_prompt import build_synthesis_nudge

logger = logging.getLogger(__name__)

# Libellés affichés dans l'UI pendant l'exécution des outils.
LIBELLES_STATUT_OUTILS: dict[str, str] = {
    "get_portfolio_positions": "Consultation de votre portefeuille",
    "get_user_context": "Lecture de votre profil",
    "get_index": "Fiche instrument",
    "list_indices": "Liste des instruments",
    "search_boursorama": "Recherche sur Boursorama",
    "get_financials_news_from_bourso": "Actualités Boursorama (cache)",
    "get_asset_news_from_yf": "Actualités Yahoo Finance",
    "get_data_from_url": "Lecture d'articles Boursorama",
    "search_past_analyses": "Recherche dans l'historique d'analyses",
    "fetch_calendar_from_bourso": "Calendrier marché",
    "create_analysis": "Enregistrement d'une analyse",
    "create_recommendation": "Création d'une recommandation",
    "create_index": "Enregistrement d'un instrument",
    "read_file": "Lecture d'un fichier partagé",
    "write_file": "Écriture d'un fichier partagé",
    "grep": "Recherche dans les fichiers",
    "write_todos": "Planification interne",
    "task": "Analyse par un expert",
}

LIBELLES_STATUT_EXPERTS: dict[str, str] = {
    "sector-analyst": "Analyse sectorielle en cours",
    "macro-strategist": "Analyse macro en cours",
    "etf-quant": "Analyse quantitative ETF en cours",
}

REPONSE_VIDE_SECOURS = (
    "Je n'ai pas pu finaliser la synthèse après les analyses. "
    "Reformulez une question précise (ex. « que faire des 300 € de liquide ? »)."
)

CHAT_RECURSION_LIMIT = 50
CHAT_HEARTBEAT_SEC = 12


@dataclass
class _StreamState:
    tool_rounds: int = 0
    task_rounds: int = 0
    last_status_label: str = "Nestor réfléchit…"


class AgentRunner:
    """Thin wrapper around the compiled Deep Agent graph."""

    def __init__(self, factory: DeepAgentFactory) -> None:
        self._agent: CompiledDeepAgent = factory.build()

    def _langgraph_config(self, context: NamRuntimeContext) -> dict[str, Any]:
        config: dict[str, Any] = {"recursion_limit": CHAT_RECURSION_LIMIT}
        if context.thread_id is not None:
            config["configurable"] = {"thread_id": context.thread_id}
        return config

    async def invoke(self, message: str, context: NamRuntimeContext) -> dict[str, Any]:
        return await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config=self._langgraph_config(context),
            context=context,
        )

    async def stream(
        self, message: str, context: NamRuntimeContext
    ) -> AsyncIterator[dict[str, Any]]:
        async for chunk in self._agent.astream(
            {"messages": [{"role": "user", "content": message}]},
            config=self._langgraph_config(context),
            context=context,
        ):
            yield chunk

    async def stream_events(
        self,
        message: str,
        context: NamRuntimeContext,
        *,
        user_question: str | None = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        """Exécute l'agent, envoie des statuts pendant l'attente, puis la réponse finale."""
        config = self._langgraph_config(context)
        state = _StreamState()
        question = (user_question or message).strip()

        yield ChatStreamEvent(type="status", status="thinking")

        async for event in self._run_graph_updates(message, context, config, state):
            yield event

        try:
            final = await self._pick_final_assistant_text(config)
            if _needs_synthesis_nudge(final, state):
                state.last_status_label = "Rédaction de la synthèse…"
                yield ChatStreamEvent(type="status", status="thinking")
                async for event in self._run_graph_updates(
                    build_synthesis_nudge(question),
                    context,
                    config,
                    state,
                ):
                    yield event
                final = await self._pick_final_assistant_text(config)

            response = _prepare_user_text(final) or REPONSE_VIDE_SECOURS
        except Exception:
            logger.exception("Chat finalization failed")
            response = REPONSE_VIDE_SECOURS

        yield ChatStreamEvent(type="status", status="writing")
        for piece in _chunk_for_stream(response):
            yield ChatStreamEvent(type="token", content=piece)

    async def _run_graph_updates(
        self,
        message: str,
        context: NamRuntimeContext,
        config: dict[str, Any],
        state: _StreamState,
    ) -> AsyncIterator[ChatStreamEvent]:
        last_ping = time.monotonic()
        async for namespace, chunk in self._agent.astream(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            context=context,
            stream_mode=["updates"],
        ):
            now = time.monotonic()
            if now - last_ping >= CHAT_HEARTBEAT_SEC:
                yield ChatStreamEvent(
                    type="status",
                    status="tool",
                    tool=state.last_status_label,
                )
                last_ping = now

            if namespace != "updates" or not isinstance(chunk, dict):
                continue

            async for event in self._iter_update_events(chunk, state):
                yield event
                last_ping = time.monotonic()

    async def _iter_update_events(
        self, chunk: dict[str, Any], state: _StreamState
    ) -> AsyncIterator[ChatStreamEvent]:
        if "model" in chunk:
            for msg in chunk["model"].get("messages", []):
                if not isinstance(msg, AIMessage):
                    continue
                if msg.tool_calls:
                    for call in msg.tool_calls:
                        name = (
                            call.get("name")
                            if isinstance(call, dict)
                            else getattr(call, "name", None)
                        )
                        if name == "task":
                            state.task_rounds += 1
                        label = _libelle_outil(call)
                        state.last_status_label = label
                        yield ChatStreamEvent(type="status", status="tool", tool=label)
        if "tools" in chunk:
            state.tool_rounds += 1
            state.last_status_label = "Analyse des résultats…"
            yield ChatStreamEvent(type="status", status="thinking")

    async def _pick_final_assistant_text(self, config: dict[str, Any]) -> str:
        snapshot = await self._agent.aget_state(config)
        messages = snapshot.values.get("messages", [])
        candidates = _assistant_text_candidates(messages)
        if not candidates:
            return ""

        substantive = [
            text
            for text in candidates
            if not _looks_like_internal_draft(text) and not _looks_like_plan_preamble(text)
        ]
        pool = substantive or candidates
        return max(pool, key=lambda text: len(text.strip()))

    async def stream_tokens(
        self, message: str, context: NamRuntimeContext
    ) -> AsyncIterator[str]:
        async for event in self.stream_events(message, context):
            if event.type == "token" and event.content:
                yield event.content


def _assistant_text_candidates(messages: list[Any]) -> list[str]:
    results: list[str] = []
    for msg in reversed(messages):
        if not isinstance(msg, AIMessage) or msg.tool_calls:
            continue
        text = _message_text(msg)
        if text:
            results.append(text)
    return results


def _needs_synthesis_nudge(text: str, state: _StreamState) -> bool:
    if state.task_rounds == 0 and state.tool_rounds == 0:
        return False
    stripped = text.strip()
    if not stripped:
        return True
    return _looks_like_plan_preamble(stripped) or _looks_like_internal_draft(stripped)


def _libelle_outil(call: object) -> str:
    name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
    if name != "task":
        return LIBELLES_STATUT_OUTILS.get(name or "", "Exécution d'un outil")

    args = call.get("args", {}) if isinstance(call, dict) else getattr(call, "args", {}) or {}
    if not isinstance(args, dict):
        return LIBELLES_STATUT_OUTILS["task"]
    subagent_type = args.get("subagent_type")
    if isinstance(subagent_type, str):
        return LIBELLES_STATUT_EXPERTS.get(subagent_type, LIBELLES_STATUT_OUTILS["task"])
    return LIBELLES_STATUT_OUTILS["task"]


def _chunk_for_stream(text: str, size: int = 48) -> list[str]:
    if len(text) <= size:
        return [text]
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            space = text.rfind(" ", start, end)
            if space > start:
                end = space + 1
        pieces.append(text[start:end])
        start = end
    return pieces


def _message_text(message: AIMessage) -> str:
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


_INTERNAL_DRAFT_MARKERS = (
    "Here is the plan",
    "Before providing any analysis",
    "I must structure",
    "Cross-Desk Ask",
    "The initial request is",
    "I must correct",
    "J'ai oublié",
    "J'ai tenté de lancer",
)

_PLAN_PREAMBLE_MARKERS = (
    "plan d'action",
    "je vais commencer",
    "afin de procéder",
    "établir un plan",
    "voici le plan",
    "je vais solliciter",
    "structured action plan",
    "here is the plan",
)

_TOOL_DUMP_MARKERS = (
    "YahooNewsItem(",
    "PositionItem(",
    "GetPortfolioPositionsOutput",
    "yahoo_symbol=",
    "resolved_from_db=",
)

_PROSE_AFTER_DUMP = re.compile(
    r"(J'|J'ai|En |Voici|Bilan|Oui|Non,|Pour |Mon |Votre |Les |D'après|Ces |"
    r"Verdict|Résumé|Synthèse|Recommandation)",
)

_UUID_PATTERN = re.compile(
    r"UUID\(['\"][0-9a-f-]{36}['\"]\)|\b[0-9a-f]{8}-[0-9a-f-]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_LATEX_TEXT_PATTERN = re.compile(r"\$\\text\{([^}]+)\}\$")
_LATEX_INLINE_PATTERN = re.compile(r"\$([^$\\]+)\$")


def _looks_like_internal_draft(text: str) -> bool:
    return any(marker in text for marker in _INTERNAL_DRAFT_MARKERS)


def _looks_like_plan_preamble(text: str) -> bool:
    lowered = text.lower().strip()
    if len(lowered) > 500:
        return False
    return any(marker in lowered for marker in _PLAN_PREAMBLE_MARKERS)


def _prepare_user_text(text: str | None, *, aggressive: bool = True) -> str | None:
    if not text:
        return None
    cleaned = _sanitize_stream_token(text, aggressive=aggressive)
    if not cleaned:
        return None
    cleaned = _UUID_PATTERN.sub("", cleaned)
    cleaned = _LATEX_TEXT_PATTERN.sub(r"\1", cleaned)
    cleaned = _LATEX_INLINE_PATTERN.sub(r"\1", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() or None


def _sanitize_stream_token(text: str | None, *, aggressive: bool = True) -> str | None:
    if not text:
        return None
    if not aggressive or not any(marker in text for marker in _TOOL_DUMP_MARKERS):
        return text
    match = _PROSE_AFTER_DUMP.search(text)
    if match and match.start() > 0:
        return text[match.start() :].lstrip() or text
    return text
