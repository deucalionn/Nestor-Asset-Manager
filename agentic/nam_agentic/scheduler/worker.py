import logging

from nam_agentic.scheduler.markets import MARKET_SESSIONS

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info(
        "NAM scheduler worker starting (stub — APScheduler deferred to market-scheduler change)"
    )
    for session in MARKET_SESSIONS:
        logger.info(
            "Registered market session: %s %s–%s %s",
            session.market.value,
            session.open_time,
            session.close_time,
            session.timezone,
        )


if __name__ == "__main__":
    main()
