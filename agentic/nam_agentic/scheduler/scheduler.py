import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from nam_agentic.enums import Market, MarketPhase
from nam_agentic.scheduler.markets import MARKET_SESSIONS, MarketSession
from nam_agentic.schemas.events import AgentEvent, EventType

logger = logging.getLogger(__name__)

MarketCallback = Callable[[AgentEvent], Awaitable[None]]


def _subtract_minutes(value: time, minutes: int) -> time:
    base = datetime.combine(datetime.min.date(), value)
    adjusted = base - timedelta(minutes=minutes)
    return adjusted.time()


def _add_minutes(value: time, minutes: int) -> time:
    base = datetime.combine(datetime.min.date(), value)
    adjusted = base + timedelta(minutes=minutes)
    return adjusted.time()


def _periodic_times(session: MarketSession) -> list[time]:
    start = _add_minutes(session.open_time, 20)
    times: list[time] = []
    cursor = datetime.combine(datetime.min.date(), start)
    close = datetime.combine(datetime.min.date(), session.close_time)
    while cursor <= close:
        times.append(cursor.time())
        cursor += timedelta(hours=2)
    return times


def register_market_jobs(
    scheduler: AsyncIOScheduler,
    callback: MarketCallback,
    *,
    timezone: str,
) -> None:
    """Register market phase cron jobs inside the agentic FastAPI process."""
    tz = ZoneInfo(timezone)

    for session in MARKET_SESSIONS:
        market = session.market

        async def _fire(phase: MarketPhase, m: Market = market) -> None:
            await callback(
                AgentEvent(
                    type=EventType.MARKET_SESSION,
                    payload={"market": m.value, "phase": phase.value},
                )
            )

        pre_open = _subtract_minutes(session.open_time, 10)
        scheduler.add_job(
            _fire,
            CronTrigger(
                hour=pre_open.hour,
                minute=pre_open.minute,
                day_of_week="mon-fri",
                timezone=tz,
            ),
            args=[MarketPhase.PRE_OPEN],
            id=f"{market.value.lower()}-pre-open",
            replace_existing=True,
        )

        post_open = _add_minutes(session.open_time, 20)
        scheduler.add_job(
            _fire,
            CronTrigger(
                hour=post_open.hour,
                minute=post_open.minute,
                day_of_week="mon-fri",
                timezone=tz,
            ),
            args=[MarketPhase.POST_OPEN],
            id=f"{market.value.lower()}-post-open",
            replace_existing=True,
        )

        for index, periodic_time in enumerate(_periodic_times(session)):
            scheduler.add_job(
                _fire,
                CronTrigger(
                    hour=periodic_time.hour,
                    minute=periodic_time.minute,
                    day_of_week="mon-fri",
                    timezone=tz,
                ),
                args=[MarketPhase.PERIODIC],
                id=f"{market.value.lower()}-periodic-{index}",
                replace_existing=True,
            )

        scheduler.add_job(
            _fire,
            CronTrigger(
                hour=session.close_time.hour,
                minute=session.close_time.minute,
                day_of_week="mon-fri",
                timezone=tz,
            ),
            args=[MarketPhase.CLOSE],
            id=f"{market.value.lower()}-close",
            replace_existing=True,
        )

        logger.info(
            "Registered market jobs for %s (%s–%s %s)",
            market.value,
            session.open_time,
            session.close_time,
            timezone,
        )


def register_news_ingest_jobs(
    scheduler: AsyncIOScheduler,
    callback: MarketCallback,
    *,
    timezone: str,
) -> None:
    """Register Boursorama session news ingest cron jobs (Europe/Paris)."""
    tz = ZoneInfo(timezone)

    eu_session = next(s for s in MARKET_SESSIONS if s.market == Market.EU)
    post_open = _add_minutes(eu_session.open_time, 20)
    periodic_times = _periodic_times(eu_session)
    mid_session = periodic_times[1] if len(periodic_times) > 1 else periodic_times[0]

    async def _session() -> None:
        await callback(
            AgentEvent(
                type=EventType.NEWS_INGEST_SESSION,
                payload={"market": Market.EU.value},
            )
        )

    for job_id, trigger_time in (
        ("news-ingest-eu-post-open", post_open),
        ("news-ingest-eu-mid", mid_session),
        ("news-ingest-eu-close", eu_session.close_time),
    ):
        scheduler.add_job(
            _session,
            CronTrigger(
                hour=trigger_time.hour,
                minute=trigger_time.minute,
                day_of_week="mon-fri",
                timezone=tz,
            ),
            id=job_id,
            replace_existing=True,
        )

    logger.info("Registered news ingest jobs (%s)", timezone)
