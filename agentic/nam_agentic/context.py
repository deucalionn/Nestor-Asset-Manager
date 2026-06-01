from dataclasses import dataclass
from uuid import UUID

from nam_agentic.enums import Market, MarketPhase


@dataclass(frozen=True)
class NamRuntimeContext:
    user_id: UUID
    market: Market | None = None
    phase: MarketPhase | None = None
    thread_id: str | None = None
