"""Chat thread message history from LangGraph checkpoints."""

from fastapi import APIRouter, HTTPException, Query

from nam_agentic.runtime import get_agent_runner

router = APIRouter(tags=["chat"])


@router.get("/chat/threads/{thread_id}/messages")
async def get_thread_messages(
    thread_id: str,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[dict[str, str]]:
    if thread_id.startswith("market:"):
        raise HTTPException(status_code=400, detail="Market cron threads are not chat conversations")

    runner = get_agent_runner()
    return await runner.get_thread_history(thread_id, limit=limit)
