"""Invoke and stream the compiled Deep Agent for chat and scheduled events."""

import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from nam_agentic.context import NamRuntimeContext
from nam_agentic.factory import CompiledDeepAgent, DeepAgentFactory
from nam_agentic.schemas.chat import ChatStreamEvent
from nam_agentic.services.chat_messages import (
    MIN_POST_TASK_SYNTHESIS_CHARS,
    find_turn_start_index,
    find_unsynthesized_task_index,
    pick_turn_assistant_text,
    sanitize_user_text,
    task_tool_result_chars,
    text_claims_missing_market_data_access,
    text_claims_async_subagent_wait,
)
from nam_agentic.services.chat_prompt import build_delegation_nudge, build_synthesis_nudge

logger = logging.getLogger(__name__)

LIBELLES_STATUT_OUTILS: dict[str, str] = {
    "get_portfolio_positions": "Consultation de votre portefeuille",
    "get_user_context": "Lecture de votre profil",
    "get_index": "Fiche instrument",
    "list_indices": "Liste des instruments",
    "search_boursorama": "Recherche sur Boursorama",
    "get_financials_news_from_bourso": "Actualités Boursorama (cache)",
    "get_asset_news_from_yf": "Actualités Yahoo Finance",
    "search_yahoo_symbol": "Recherche symbole Yahoo",
    "get_asset_price_from_yf": "Cours Yahoo Finance",
    "get_company_financials_from_yf": "Comptes et ratios Yahoo Finance",
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
    "Je n'ai pas pu produire de réponse finale. Reformulez votre question de façon précise."
)

CHAT_RECURSION_LIMIT = 50
CHAT_HEARTBEAT_SEC = 12
# Deep Agents streaming: https://docs.langchain.com/oss/python/deepagents/streaming
MODEL_UPDATE_NODES = frozenset({"model", "model_request"})


@dataclass
class _ActiveSubagent:
    subagent_type: str
    description: str
    status: str = "pending"  # pending | running | complete


@dataclass
class _StreamState:
    tool_rounds: int = 0
    task_rounds: int = 0
    last_status_label: str = "Nestor réfléchit…"
    tools_called: set[str] = field(default_factory=set)
    pending_subagent: str | None = None
    subagents_invoked: list[str] = field(default_factory=list)
    last_task_result_chars: int = 0
    active_subagents: dict[str, _ActiveSubagent] = field(default_factory=dict)


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
        thread_id: str | None = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        config = self._langgraph_config(context)
        state = _StreamState()
        question = (user_question or message).strip()
        tid = thread_id or context.thread_id

        logger.info(
            "chat.turn.start thread_id=%s user_id=%s question=%.120s",
            tid,
            context.user_id,
            question,
        )

        yield ChatStreamEvent(type="status", status="thinking", thread_id=tid)

        async for event in self._run_graph_updates(message, context, config, state, tid):
            yield event

        try:
            messages = await self._get_thread_messages(config)
            turn_start = find_turn_start_index(messages, question)
            final = pick_turn_assistant_text(messages, turn_start)
            if state.task_rounds == 0:
                state.last_task_result_chars = max(
                    state.last_task_result_chars, task_tool_result_chars(messages)
                )
            prior_task_pending = find_unsynthesized_task_index(messages) is not None

            if _needs_delegation_nudge(final, state):
                reason = "missing_market_api_fiction" if text_claims_missing_market_data_access(final) else "no_task"
                logger.warning(
                    "chat.delegation.nudge thread_id=%s reason=%s tools=%s",
                    tid,
                    reason,
                    sorted(state.tools_called),
                )
                state.last_status_label = "Délégation à un expert…"
                yield ChatStreamEvent(type="status", status="thinking", thread_id=tid)
                async for event in self._run_graph_updates(
                    build_delegation_nudge(question),
                    context,
                    config,
                    state,
                    tid,
                ):
                    yield event
                messages = await self._get_thread_messages(config)
                turn_start = find_turn_start_index(messages, question)
                final = pick_turn_assistant_text(messages, turn_start)
                prior_task_pending = find_unsynthesized_task_index(messages) is not None

            if _needs_synthesis_nudge(final, state, messages):
                reason = "async_wait_fiction" if text_claims_async_subagent_wait(final) else "thin_or_missing"
                logger.info(
                    "chat.synthesis.nudge thread_id=%s reason=%s final_chars=%d "
                    "task_result_chars=%d prior_task_pending=%s",
                    tid,
                    reason,
                    len(final.strip()),
                    state.last_task_result_chars,
                    prior_task_pending,
                )
                state.last_status_label = "Rédaction de la synthèse…"
                yield ChatStreamEvent(type="status", status="thinking", thread_id=tid)
                async for event in self._run_graph_updates(
                    build_synthesis_nudge(question, from_prior_turn=prior_task_pending),
                    context,
                    config,
                    state,
                    tid,
                ):
                    yield event
                messages = await self._get_thread_messages(config)
                turn_start = find_turn_start_index(messages, question)
                final = pick_turn_assistant_text(messages, turn_start)

            response = sanitize_user_text(final) or REPONSE_VIDE_SECOURS
            if text_claims_async_subagent_wait(response or ""):
                logger.warning(
                    "chat.async_wait.fiction thread_id=%s — forcing synthesis retry",
                    tid,
                )
                async for event in self._run_graph_updates(
                    build_synthesis_nudge(question, from_prior_turn=True),
                    context,
                    config,
                    state,
                    tid,
                ):
                    yield event
                messages = await self._get_thread_messages(config)
                turn_start = find_turn_start_index(messages, question)
                final = pick_turn_assistant_text(messages, turn_start)
                response = sanitize_user_text(final) or REPONSE_VIDE_SECOURS
        except Exception:
            logger.exception("Chat finalization failed thread_id=%s", tid)
            response = REPONSE_VIDE_SECOURS

        logger.info(
            "chat.turn.done thread_id=%s task_rounds=%d subagents=%s tools=%s response_chars=%d",
            tid,
            state.task_rounds,
            state.subagents_invoked,
            sorted(state.tools_called),
            len(response),
        )
        if state.task_rounds == 0 and "fetch_calendar_from_bourso" not in state.tools_called:
            logger.debug(
                "chat.turn.no_subagent thread_id=%s tools=%s",
                tid,
                sorted(state.tools_called),
            )

        yield ChatStreamEvent(type="status", status="writing", thread_id=tid)
        for piece in _chunk_for_stream(response):
            yield ChatStreamEvent(type="token", content=piece, thread_id=tid)

    async def _run_graph_updates(
        self,
        message: str,
        context: NamRuntimeContext,
        config: dict[str, Any],
        state: _StreamState,
        thread_id: str | None,
    ) -> AsyncIterator[ChatStreamEvent]:
        """Stream graph progress via LangGraph v2 updates + subgraph namespaces.

        Uses ``stream_mode="updates"`` with ``subgraphs=True`` and ``version="v2"``
        (Deep Agents streaming doc). Intermediate PM drafts must not reach the user;
        only status labels are emitted during the graph run. Final text is picked
        after the graph completes (and optional synthesis nudge).
        """
        last_ping = time.monotonic()
        async for item in self._agent.astream(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            context=context,
            stream_mode=["updates"],
            subgraphs=True,
            version="v2",
        ):
            parsed = _coerce_updates_stream_part(item)
            if parsed is None:
                continue
            namespace, chunk = parsed

            async for event in self._iter_update_events(chunk, state, thread_id, namespace):
                yield event
                last_ping = time.monotonic()

            now = time.monotonic()
            if now - last_ping >= CHAT_HEARTBEAT_SEC:
                yield ChatStreamEvent(
                    type="status",
                    status="tool",
                    tool=state.last_status_label,
                    thread_id=thread_id,
                )
                last_ping = now

    async def _iter_update_events(
        self,
        chunk: dict[str, Any],
        state: _StreamState,
        thread_id: str | None,
        namespace: tuple[str, ...],
    ) -> AsyncIterator[ChatStreamEvent]:
        is_subagent = any(segment.startswith("tools:") for segment in namespace)

        if is_subagent:
            pregel_id = next(
                (segment.split(":", 1)[1] for segment in namespace if segment.startswith("tools:")),
                None,
            )
            for sub in state.active_subagents.values():
                if sub.status == "pending":
                    sub.status = "running"
                    logger.info(
                        "subagent.running thread_id=%s subagent=%s pregel=%s",
                        thread_id,
                        sub.subagent_type,
                        pregel_id,
                    )
                    break
            for node_name in chunk:
                if node_name.startswith("__"):
                    continue
                logger.debug(
                    "chat.subgraph.step thread_id=%s namespace=%s node=%s",
                    thread_id,
                    namespace,
                    node_name,
                )

        for node_name, node_data in chunk.items():
            if node_name.startswith("__") or not isinstance(node_data, dict):
                continue

            if node_name in MODEL_UPDATE_NODES and not namespace:
                async for event in self._iter_model_update_events(node_data, state, thread_id):
                    yield event
            elif node_name == "tools" and not namespace:
                async for event in self._iter_tools_update_events(node_data, state, thread_id):
                    yield event

    async def _iter_model_update_events(
        self,
        node_data: dict[str, Any],
        state: _StreamState,
        thread_id: str | None,
    ) -> AsyncIterator[ChatStreamEvent]:
        for msg in node_data.get("messages", []):
            if not isinstance(msg, AIMessage):
                continue
            if not msg.tool_calls:
                continue
            for call in msg.tool_calls:
                name = (
                    call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
                )
                call_id = call.get("id") if isinstance(call, dict) else getattr(call, "id", None)
                if isinstance(name, str):
                    state.tools_called.add(name)
                if name == "task":
                    state.task_rounds += 1
                    args = (
                        call.get("args", {})
                        if isinstance(call, dict)
                        else getattr(call, "args", {}) or {}
                    )
                    subagent_type = args.get("subagent_type") if isinstance(args, dict) else None
                    description = args.get("description", "") if isinstance(args, dict) else ""
                    if isinstance(subagent_type, str):
                        state.pending_subagent = subagent_type
                        state.subagents_invoked.append(subagent_type)
                        if isinstance(call_id, str):
                            state.active_subagents[call_id] = _ActiveSubagent(
                                subagent_type=subagent_type,
                                description=str(description)[:200],
                                status="pending",
                            )
                        logger.info(
                            "subagent.pending thread_id=%s subagent=%s call_id=%s description=%.200s",
                            thread_id,
                            subagent_type,
                            call_id,
                            description,
                        )
                label = _libelle_outil(call)
                state.last_status_label = label
                yield ChatStreamEvent(
                    type="status", status="tool", tool=label, thread_id=thread_id
                )

    async def _iter_tools_update_events(
        self,
        node_data: dict[str, Any],
        state: _StreamState,
        thread_id: str | None,
    ) -> AsyncIterator[ChatStreamEvent]:
        state.tool_rounds += 1
        for msg in node_data.get("messages", []):
            if not isinstance(msg, ToolMessage):
                continue
            if getattr(msg, "name", None) == "task":
                content = msg.content
                if isinstance(content, str):
                    state.last_task_result_chars = len(content)
                elif content is not None:
                    state.last_task_result_chars = len(str(content))
                sub = state.active_subagents.get(msg.tool_call_id)
                if sub:
                    sub.status = "complete"
                logger.info(
                    "subagent.complete thread_id=%s subagent=%s call_id=%s "
                    "tool_round=%d result_chars=%d preview=%.120s",
                    thread_id,
                    state.pending_subagent or (sub.subagent_type if sub else "?"),
                    msg.tool_call_id,
                    state.tool_rounds,
                    state.last_task_result_chars,
                    content if isinstance(content, str) else str(content),
                )
                state.pending_subagent = None
        state.last_status_label = "Analyse des résultats…"
        yield ChatStreamEvent(type="status", status="thinking", thread_id=thread_id)

    async def _get_thread_messages(self, config: dict[str, Any]) -> list[Any]:
        snapshot = await self._agent.aget_state(config)
        return snapshot.values.get("messages", [])

    async def get_thread_history(
        self, thread_id: str, *, limit: int = 100
    ) -> list[dict[str, str]]:
        from nam_agentic.services.checkpoint_messages import to_chat_history

        config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
        snapshot = await self._agent.aget_state(config)
        messages = snapshot.values.get("messages", [])
        return to_chat_history(messages, limit=limit)


def _coerce_updates_stream_part(item: Any) -> tuple[tuple[str, ...], dict[str, Any]] | None:
    """Normalize LangGraph v2 StreamPart or legacy tuple chunks to (namespace, data)."""
    if isinstance(item, dict) and item.get("type") == "updates":
        data = item.get("data")
        if isinstance(data, dict):
            ns = item.get("ns") or ()
            return (tuple(ns), data)
        return None
    if isinstance(item, tuple):
        if len(item) == 3:
            ns, mode, data = item
            if mode == "updates" and isinstance(data, dict):
                return (tuple(ns) if ns else (), data)
        elif len(item) == 2:
            mode, data = item
            if mode == "updates" and isinstance(data, dict):
                return ((), data)
    return None


def _needs_synthesis_nudge(text: str, state: _StreamState, messages: list[Any]) -> bool:
    """Re-run the PM when synthesis is missing, too thin, or architecturally invalid."""
    stripped = text.strip()
    if text_claims_async_subagent_wait(stripped):
        return True
    if find_unsynthesized_task_index(messages) is not None and (
        state.task_rounds == 0 or len(stripped) < MIN_POST_TASK_SYNTHESIS_CHARS
    ):
        return True
    if state.task_rounds == 0:
        return False
    if not stripped:
        return True
    if state.last_task_result_chars and len(stripped) < state.last_task_result_chars * 0.25:
        return True
    return len(stripped) < MIN_POST_TASK_SYNTHESIS_CHARS


def _needs_delegation_nudge(text: str, state: _StreamState) -> bool:
    """PM tried to answer without task() — force a delegation pass."""
    if state.task_rounds > 0:
        return False
    if text_claims_missing_market_data_access(text) or text_claims_async_subagent_wait(text):
        return True
    if text.strip():
        return False
    if state.tools_called <= {"fetch_calendar_from_bourso"}:
        return False
    return True


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
