import logging
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from nam_agentic.context import NamRuntimeContext
from nam_agentic.enums import MarketPhase
from nam_agentic.runtime import get_agent_runner
from nam_agentic.schemas.chat import ChatStreamEvent, ChatStreamRequest
from nam_agentic.services.chat_prompt import build_chat_message
from nam_agentic.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


async def _stream_ndjson(events: AsyncIterator[ChatStreamEvent]) -> AsyncIterator[str]:
    async for event in events:
        yield event.model_dump_json(exclude_none=True) + "\n"


@router.post("/chat/stream")
async def chat_stream(body: ChatStreamRequest) -> StreamingResponse:
    thread_id = body.thread_id or str(uuid4())
    user_id = body.user_id or UUID(settings.default_user_id)
    context = NamRuntimeContext(
        user_id=user_id,
        phase=MarketPhase.CHAT,
        thread_id=thread_id,
    )
    runner = get_agent_runner()

    async def events() -> AsyncIterator[ChatStreamEvent]:
        try:
            async for event in runner.stream_events(
                build_chat_message(body.content),
                context=context,
                user_question=body.content,
            ):
                if event.type == "token":
                    yield ChatStreamEvent(type="token", content=event.content)
                elif event.type == "status":
                    yield ChatStreamEvent(
                        type="status",
                        status=event.status,
                        tool=event.tool,
                    )
            yield ChatStreamEvent(type="done", thread_id=thread_id)
        except Exception as exc:
            logger.exception("Chat stream failed")
            yield ChatStreamEvent(type="error", message=str(exc))

    return StreamingResponse(
        _stream_ndjson(events()),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
