"""WebSocket chat proxy — front connects here; streams to nam-agentic ``/chat/stream``."""

import json
import logging
from uuid import UUID

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from nam_api.dependencies import get_db_session, get_user_service
from nam_api.schemas.chat import ChatWsClientMessage, ChatWsServerMessage
from nam_api.services.chat_thread_service import ChatThreadService
from nam_api.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])
_chat_thread_service = ChatThreadService()


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
                message = ChatWsClientMessage.model_validate(payload)
            except (json.JSONDecodeError, ValidationError) as exc:
                await websocket.send_text(
                    ChatWsServerMessage(type="error", message=str(exc)).model_dump_json(
                        exclude_none=True
                    )
                )
                continue

            stream_url = f"{settings.agentic_url.rstrip('/')}/chat/stream"
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream(
                        "POST",
                        stream_url,
                        json=message.model_dump(exclude_none=True),
                    ) as response:
                        if response.status_code != 200:
                            body = await response.aread()
                            detail = body.decode() or response.reason_phrase
                            await websocket.send_text(
                                ChatWsServerMessage(
                                    type="error",
                                    message=f"Agentic error {response.status_code}: {detail}",
                                ).model_dump_json(exclude_none=True)
                            )
                            continue

                        saw_terminal = False
                        async for line in response.aiter_lines():
                            if not line.strip():
                                continue
                            try:
                                payload = json.loads(line)
                            except json.JSONDecodeError:
                                payload = {}
                            if payload.get("type") in ("done", "error"):
                                saw_terminal = True
                                if payload.get("type") == "done":
                                    tid = payload.get("thread_id") or message.thread_id
                                    if tid:
                                        await _touch_thread_metadata(tid, message.content)
                            await websocket.send_text(line)
                        if not saw_terminal:
                            await websocket.send_text(
                                ChatWsServerMessage(
                                    type="error",
                                    message=(
                                        "Le flux agent s'est interrompu avant la réponse finale. "
                                        "Réessayez dans un instant."
                                    ),
                                ).model_dump_json(exclude_none=True)
                            )
            except httpx.HTTPError as exc:
                logger.exception("Chat proxy failed to reach agentic")
                await websocket.send_text(
                    ChatWsServerMessage(
                        type="error",
                        message=f"Agentic unreachable: {exc}",
                    ).model_dump_json(exclude_none=True)
                )
    except WebSocketDisconnect:
        logger.debug("Chat WebSocket disconnected")


async def _touch_thread_metadata(thread_id: str, user_message: str) -> None:
    try:
        user_service = get_user_service()
        async for session in get_db_session():
            user_id = await user_service.require_user_id(session)
            await _chat_thread_service.touch_after_message(
                session,
                user_id,
                UUID(thread_id),
                user_message,
            )
            await session.commit()
            break
    except Exception:
        logger.exception("Failed to upsert chat thread metadata")
