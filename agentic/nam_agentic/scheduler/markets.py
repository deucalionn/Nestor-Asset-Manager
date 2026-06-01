from dataclasses import dataclass
from datetime import time

from nam_agentic.enums import Market


@dataclass(frozen=True)
class MarketSession:
    market: Market
    open_time: time
    close_time: time
    timezone: str = "Europe/Paris"


MARKET_SESSIONS: tuple[MarketSession, ...] = (
    MarketSession(market=Market.EU, open_time=time(9, 0), close_time=time(17, 30)),
    MarketSession(market=Market.US, open_time=time(15, 30), close_time=time(22, 0)),
    MarketSession(market=Market.ASIA, open_time=time(2, 0), close_time=time(8, 0)),
)
