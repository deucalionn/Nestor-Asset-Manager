from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatStreamRequest(BaseModel):
    content: str = Field(min_length=1, max_length=16000)
    thread_id: str | None = None
    user_id: UUID | None = None


class ChatStreamEvent(BaseModel):
    type: Literal["token", "status", "done", "error"]
    content: str | None = None
    status: Literal["thinking", "tool", "writing"] | None = None
    tool: str | None = None
    thread_id: str | None = None
    message: str | None = None
