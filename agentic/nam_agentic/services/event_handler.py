import logging
from pathlib import Path
from uuid import UUID

from nam_agentic.context import NamRuntimeContext
from nam_agentic.enums import Market, MarketPhase
from nam_agentic.schemas.events import AgentEvent, EventType
from nam_agentic.settings import settings

logger = logging.getLogger(__name__)


class EventHandler:
    """Routes inbound events to agent runs.

    Skeleton only — wire AgentRunner.invoke() in each _on_* method when
    implementing agents, subagents, and tools (hand-owned).
    """

    def __init__(self, workspace_dir: Path | None = None) -> None:
        self._workspace_dir = workspace_dir or settings.agent_workspace_dir

    async def handle(self, event: AgentEvent) -> None:
        self._workspace_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Event received: type=%s user_id=%s", event.type, event.user_id)

        match event.type:
            case EventType.USER_PROFILE_CREATED:
                await self._on_user_profile_created(event)
            case EventType.USER_PROFILE_UPDATED:
                await self._on_user_profile_updated(event)
            case EventType.CHAT_MESSAGE:
                await self._on_chat_message(event)
            case EventType.MARKET_SESSION:
                await self._on_market_session(event)

    async def _on_user_profile_created(self, event: AgentEvent) -> None:
        user_id = event.user_id or UUID(settings.default_user_id)
        logger.info(
            "Onboarding run queued for user %s — agent writes workspace files",
            user_id,
        )
        # Hand-owned: AgentRunner.invoke(onboarding prompt, context=...)
        _ = NamRuntimeContext(user_id=user_id, phase=MarketPhase.MANUAL)

    async def _on_user_profile_updated(self, event: AgentEvent) -> None:
        user_id = event.user_id or UUID(settings.default_user_id)
        logger.info("Profile refresh run queued for user %s", user_id)
        _ = NamRuntimeContext(user_id=user_id, phase=MarketPhase.MANUAL)

    async def _on_chat_message(self, event: AgentEvent) -> None:
        user_id = event.user_id or UUID(settings.default_user_id)
        logger.info("Chat message event for user %s", user_id)
        _ = NamRuntimeContext(
            user_id=user_id,
            phase=MarketPhase.CHAT,
            thread_id=event.payload.get("thread_id"),
        )

    async def _on_market_session(self, event: AgentEvent) -> None:
        market = Market(event.payload["market"])
        phase = MarketPhase(event.payload["phase"])
        user_id = UUID(settings.default_user_id)
        logger.info("Market session event: market=%s phase=%s", market.value, phase.value)
        _ = NamRuntimeContext(user_id=user_id, market=market, phase=phase)
