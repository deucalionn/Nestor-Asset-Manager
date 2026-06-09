import logging
from pathlib import Path
from uuid import UUID

from nam_agentic.context import NamRuntimeContext
from nam_agentic.enums import Market, MarketPhase
from nam_agentic.schemas.events import AgentEvent, EventType
from nam_agentic.settings import settings
from nam_agentic.tools.services.boursorama.ingest import NewsIngestService
from nam_db.session import async_session_factory
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class EventHandler:
    """Routes inbound events to agent runs.

    Skeleton only — wire AgentRunner.invoke() in each _on_* method when
    implementing agents, subagents, and tools (hand-owned).
    """

    def __init__(
        self,
        workspace_dir: Path | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._workspace_dir = workspace_dir or settings.agent_workspace_dir
        self._session_factory = session_factory or async_session_factory
        self._news_ingest = NewsIngestService(self._session_factory)

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
            case EventType.NEWS_INGEST_DAILY:
                await self._on_news_ingest_daily(event)
            case EventType.NEWS_INGEST_SESSION:
                await self._on_news_ingest_session(event)

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

    async def _on_news_ingest_daily(self, event: AgentEvent) -> None:
        if not settings.news_ingest_enabled:
            logger.info("News ingest disabled — skipping daily ingest")
            return
        run_id = await self._news_ingest.ingest_daily()
        logger.info("Daily news ingest completed run_id=%s (event=%s)", run_id, event.type)

    async def _on_news_ingest_session(self, event: AgentEvent) -> None:
        if not settings.news_ingest_enabled:
            logger.info("News ingest disabled — skipping session ingest")
            return
        market = event.payload.get("market", Market.EU.value)
        run_id = await self._news_ingest.ingest_session()
        logger.info(
            "Session news ingest completed run_id=%s market=%s",
            run_id,
            market,
        )
