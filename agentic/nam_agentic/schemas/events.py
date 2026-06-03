from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(StrEnum):
    USER_PROFILE_CREATED = "user.profile.created"
    USER_PROFILE_UPDATED = "user.profile.updated"
    CHAT_MESSAGE = "chat.message"
    MARKET_SESSION = "market.session"


class AgentEvent(BaseModel):
    type: EventType
    user_id: UUID | None = None
    # a voir car Any, peut etre on peut faire un type plus precis ou alors on caste en fonction du type de l'event dans le service nécessaire
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentEventAccepted(BaseModel):
    type: EventType
    status: str = "accepted"
