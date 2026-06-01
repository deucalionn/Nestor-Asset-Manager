from enum import Enum


class Market(str, Enum):
    EU = "EU"
    US = "US"
    ASIA = "ASIA"


class MarketPhase(str, Enum):
    PRE_OPEN = "PRE_OPEN"
    POST_OPEN = "POST_OPEN"
    PERIODIC = "PERIODIC"
    CLOSE = "CLOSE"
    CHAT = "CHAT"
    MANUAL = "MANUAL"
