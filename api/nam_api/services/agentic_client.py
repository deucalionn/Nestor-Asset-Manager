import logging
from typing import Any
from uuid import UUID

import httpx

from nam_api.settings import settings

logger = logging.getLogger(__name__)


async def emit_agent_event(
    event_type: str,
    *,
    user_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Fire-and-forget notification to nam-agentic. Failures are logged, not raised."""
    url = f"{settings.agentic_url.rstrip('/')}/events"
    body: dict[str, Any] = {
        "type": event_type,
        "payload": payload or {},
    }
    if user_id is not None:
        body["user_id"] = str(user_id)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, json=body)
            response.raise_for_status()
    except Exception as exc:
        logger.warning("Could not reach nam-agentic at %s: %s", url, exc)
