from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(StrEnum):
    USER_PROFILE_CREATED = "user.profile.created"
    USER_PROFILE_UPDATED = "user.profile.updated"
    CHAT_MESSAGE = "chat.message"
    MARKET_SESSION = "market.session"
    NEWS_INGEST_SESSION = "news.ingest.session"


class AgentEvent(BaseModel):
    type: EventType
    user_id: UUID | None = None
    # Typed per event in handlers when needed (v1 keeps a loose dict).
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentEventAccepted(BaseModel):
    type: EventType
    status: str = "accepted"
