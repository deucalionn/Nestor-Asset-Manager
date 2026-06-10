"""Inbound event bus — profile lifecycle, market cron, and news ingest."""

import logging
from datetime import date
from pathlib import Path
from uuid import UUID

from nam_agentic.context import NamRuntimeContext
from nam_agentic.enums import Market, MarketPhase
from nam_agentic.runner import AgentRunner
from nam_agentic.schemas.events import AgentEvent, EventType
from nam_agentic.settings import settings
from nam_agentic.tools.services.boursorama.ingest import NewsIngestService
from nam_db.session import async_session_factory
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


def market_session_seed_message(market: Market, phase: MarketPhase) -> str:
    return (
        f"Run the {market.value} {phase.value} portfolio cycle. "
        "Follow PORTFOLIO.md: load user context, refresh the shared calendar if stale, "
        "then delegate to subagents as needed."
    )


def market_thread_id(
    market: Market,
    phase: MarketPhase,
    session_date: date | None = None,
) -> str:
    day = session_date or date.today()
    return f"market:{market.value}:{phase.value}:{day.isoformat()}"


ONBOARDING_SEED_MESSAGE = (
    "Onboarding run for a new NAM user. Follow PORTFOLIO.md workspace rules:\n"
    "1. Call get_user_context (profile already exists in PostgreSQL via POST /setup).\n"
    "2. Write interpreted goals and strategy to /user/{user_id}/USER_GOALS.md via write_file.\n"
    "3. Summarize the user profile for future portfolio cycles."
)

PROFILE_REFRESH_SEED_MESSAGE = (
    "Profile refresh run after PUT /profile. Follow PORTFOLIO.md workspace rules:\n"
    "1. Call get_user_context for the updated profile.\n"
    "2. Rewrite (replace entire contents of) /user/{user_id}/USER_GOALS.md via write_file.\n"
    "3. Summarize what changed for future portfolio cycles."
)


class EventHandler:
    """Routes inbound events to agent runs or background ingest."""

    def __init__(
        self,
        workspace_dir: Path | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        agent_runner: AgentRunner | None = None,
    ) -> None:
        self._workspace_dir = workspace_dir or settings.agent_workspace_dir
        self._session_factory = session_factory or async_session_factory
        self._news_ingest = NewsIngestService(self._session_factory)
        self._agent_runner = agent_runner

    def _ensure_workspace(self, user_id: UUID | None = None) -> None:
        self._workspace_dir.mkdir(parents=True, exist_ok=True)
        (self._workspace_dir / "shared").mkdir(parents=True, exist_ok=True)
        if user_id is not None:
            (self._workspace_dir / "user" / str(user_id)).mkdir(parents=True, exist_ok=True)

    async def handle(self, event: AgentEvent) -> None:
        user_id = event.user_id or UUID(settings.default_user_id)
        self._ensure_workspace(user_id)
        logger.info("Event received: type=%s user_id=%s", event.type, event.user_id)

        match event.type:
            case EventType.USER_PROFILE_CREATED:
                await self._on_user_profile_created(event)
            case EventType.USER_PROFILE_UPDATED:
                await self._on_user_profile_updated(event)
            case EventType.MARKET_SESSION:
                await self._on_market_session(event)
            case EventType.NEWS_INGEST_SESSION:
                await self._on_news_ingest_session(event)

    async def _invoke_agent(self, message: str, context: NamRuntimeContext) -> None:
        if self._agent_runner is None:
            logger.warning("AgentRunner not configured — skipping invoke")
            return
        await self._agent_runner.invoke(message, context=context)

    async def _on_user_profile_created(self, event: AgentEvent) -> None:
        user_id = event.user_id or UUID(settings.default_user_id)
        self._ensure_workspace(user_id)
        context = NamRuntimeContext(user_id=user_id, phase=MarketPhase.MANUAL)
        message = ONBOARDING_SEED_MESSAGE.format(user_id=user_id)
        logger.info("Onboarding agent run for user %s", user_id)
        await self._invoke_agent(message, context)

    async def _on_user_profile_updated(self, event: AgentEvent) -> None:
        user_id = event.user_id or UUID(settings.default_user_id)
        self._ensure_workspace(user_id)
        context = NamRuntimeContext(user_id=user_id, phase=MarketPhase.MANUAL)
        message = PROFILE_REFRESH_SEED_MESSAGE.format(user_id=user_id)
        logger.info("Profile refresh agent run for user %s", user_id)
        await self._invoke_agent(message, context)

    async def _on_market_session(self, event: AgentEvent) -> None:
        market = Market(event.payload["market"])
        phase = MarketPhase(event.payload["phase"])
        user_id = UUID(settings.default_user_id)
        thread_id = market_thread_id(market, phase)
        context = NamRuntimeContext(
            user_id=user_id,
            market=market,
            phase=phase,
            thread_id=thread_id,
        )
        logger.info(
            "Market session event: market=%s phase=%s thread_id=%s",
            market.value,
            phase.value,
            thread_id,
        )
        message = market_session_seed_message(market, phase)
        await self._invoke_agent(message, context)

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
