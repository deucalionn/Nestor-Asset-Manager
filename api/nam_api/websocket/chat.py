import json
import logging

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from nam_api.schemas.chat import ChatWsClientMessage, ChatWsServerMessage
from nam_api.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


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
