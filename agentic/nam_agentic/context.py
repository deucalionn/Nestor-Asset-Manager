"""LangGraph runtime context passed to tools and graph invocations."""

from dataclasses import dataclass
from uuid import UUID

from nam_agentic.enums import Market, MarketPhase


@dataclass(frozen=True)
class NamRuntimeContext:
    """User scope, market phase, and LangGraph ``thread_id`` for a single run."""

    user_id: UUID
    market: Market | None = None
    phase: MarketPhase | None = None
    thread_id: str | None = None
