from fastapi import APIRouter, BackgroundTasks, status
from nam_agentic.dependencies import event_handler
from nam_agentic.schemas.events import AgentEvent, AgentEventAccepted

router = APIRouter(tags=["events"])


@router.post(
    "/events",
    response_model=AgentEventAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_event(
    event: AgentEvent,
    background_tasks: BackgroundTasks,
) -> AgentEventAccepted:
    background_tasks.add_task(event_handler.handle, event)
    return AgentEventAccepted(type=event.type)
