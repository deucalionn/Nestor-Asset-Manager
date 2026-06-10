from pydantic import BaseModel, Field


class ChatWsClientMessage(BaseModel):
    content: str = Field(min_length=1)
    thread_id: str | None = None


class ChatWsServerMessage(BaseModel):
    type: str
    content: str | None = None
    thread_id: str | None = None
    message: str | None = None
