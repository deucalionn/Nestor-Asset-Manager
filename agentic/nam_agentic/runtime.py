"""Process-wide holder for the compiled agent graph and event router.

Set once in ``main.lifespan`` via ``set_runtime``; read from routers and
``dependencies`` while the FastAPI app is running.
"""

from dataclasses import dataclass

from nam_agentic.runner import AgentRunner
from nam_agentic.services.event_handler import EventHandler


@dataclass
class AgentRuntime:
    """Live ``AgentRunner`` and ``EventHandler`` for the current process."""

    agent_runner: AgentRunner
    event_handler: EventHandler


_runtime: AgentRuntime | None = None


def set_runtime(runtime: AgentRuntime) -> None:
    global _runtime
    _runtime = runtime


def get_runtime() -> AgentRuntime:
    if _runtime is None:
        msg = "Agent runtime is not initialized — nam-agentic lifespan has not started"
        raise RuntimeError(msg)
    return _runtime


def get_agent_runner() -> AgentRunner:
    return get_runtime().agent_runner


def get_event_handler() -> EventHandler:
    return get_runtime().event_handler
