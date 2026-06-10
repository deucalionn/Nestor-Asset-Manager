from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from nam_api.dependencies import get_db_session, get_singleton_user_id
from nam_api.exceptions import NotFoundError
from nam_api.schemas.chat_thread import (
    ChatMessageRead,
    ChatThreadCreate,
    ChatThreadRead,
    ChatThreadUpdate,
)
from nam_api.services.chat_thread_service import ChatThreadService
from nam_api.settings import settings

router = APIRouter(prefix="/chat/threads", tags=["chat"])


def get_chat_thread_service() -> ChatThreadService:
    return ChatThreadService()


@router.get("", response_model=list[ChatThreadRead])
async def list_chat_threads(
    user_id: UUID = Depends(get_singleton_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: ChatThreadService = Depends(get_chat_thread_service),
) -> list[ChatThreadRead]:
    threads = await service.list_for_user(session, user_id)
    return [ChatThreadRead.model_validate(t) for t in threads]


@router.post("", response_model=ChatThreadRead, status_code=201)
async def create_chat_thread(
    body: ChatThreadCreate,
    user_id: UUID = Depends(get_singleton_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: ChatThreadService = Depends(get_chat_thread_service),
) -> ChatThreadRead:
    thread = await service.create(session, user_id, title=body.title)
    await session.commit()
    await session.refresh(thread)
    return ChatThreadRead.model_validate(thread)


@router.patch("/{thread_id}", response_model=ChatThreadRead)
async def update_chat_thread(
    thread_id: UUID,
    body: ChatThreadUpdate,
    user_id: UUID = Depends(get_singleton_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: ChatThreadService = Depends(get_chat_thread_service),
) -> ChatThreadRead:
    thread = await service.update_title(session, user_id, thread_id, body.title)
    await session.commit()
    return ChatThreadRead.model_validate(thread)


@router.delete("/{thread_id}", status_code=204, response_class=Response)
async def delete_chat_thread(
    thread_id: UUID,
    user_id: UUID = Depends(get_singleton_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: ChatThreadService = Depends(get_chat_thread_service),
) -> Response:
    await service.delete(session, user_id, thread_id)
    await session.commit()
    return Response(status_code=204)


@router.get("/{thread_id}/messages", response_model=list[ChatMessageRead])
async def list_thread_messages(
    thread_id: UUID,
    user_id: UUID = Depends(get_singleton_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: ChatThreadService = Depends(get_chat_thread_service),
) -> list[ChatMessageRead]:
    await service.require(session, user_id, thread_id)
    url = f"{settings.agentic_url.rstrip('/')}/chat/threads/{thread_id}/messages"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
    if response.status_code == 404:
        return []
    if response.status_code != 200:
        raise NotFoundError("Conversation history unavailable")
    payload = response.json()
    return [ChatMessageRead.model_validate(row) for row in payload]
