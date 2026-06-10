"""Runtime accessors — populated during FastAPI lifespan startup."""

from nam_agentic.runtime import get_agent_runner, get_event_handler, get_runtime

__all__ = ["get_agent_runner", "get_event_handler", "get_runtime"]
