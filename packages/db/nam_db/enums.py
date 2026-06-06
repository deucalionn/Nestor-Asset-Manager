from enum import Enum


class Strategy(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    BALANCED = "BALANCED"
    GROWTH = "GROWTH"
    AGGRESSIVE = "AGGRESSIVE"


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class AgentRole(str, Enum):
    PORTFOLIO_MANAGER = "PORTFOLIO_MANAGER"
    SECTOR_ANALYST = "SECTOR_ANALYST"
    MACRO_STRATEGIST = "MACRO_STRATEGIST"
    ETF_QUANT_SPECIALIST = "ETF_QUANT_SPECIALIST"


class SubAgentRole(str, Enum):
    """Roles allowed to author analyses (subset of AgentRole — excludes PM)."""

    SECTOR_ANALYST = "SECTOR_ANALYST"
    MACRO_STRATEGIST = "MACRO_STRATEGIST"
    ETF_QUANT_SPECIALIST = "ETF_QUANT_SPECIALIST"


class RecommendationType(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


class RecommendationStatus(str, Enum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"


class AnalysisTrigger(str, Enum):
    MARKET_SESSION = "MARKET_SESSION"
    NEWS_EVENT = "NEWS_EVENT"
    MANUAL = "MANUAL"
    TASK = "TASK"
