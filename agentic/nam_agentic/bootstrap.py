"""Wire the agent runtime at process startup (called from ``main.lifespan``)."""

from uuid import UUID

from langgraph.checkpoint.base import BaseCheckpointSaver
from nam_db.session import async_session_factory

from nam_agentic.agent_factory import build_deep_agent_factory
from nam_agentic.context import NamRuntimeContext
from nam_agentic.factory import configure_nam_harness_profile
from nam_agentic.runner import AgentRunner
from nam_agentic.services.event_handler import EventHandler
from nam_agentic.settings import settings
from nam_agentic.tools.registry import ToolRegistry


def build_agent_runner(checkpointer: BaseCheckpointSaver) -> AgentRunner:
    """Assemble tools, Deep Agent graph, and runner for a live Postgres checkpointer."""
    configure_nam_harness_profile()
    context = NamRuntimeContext(user_id=UUID(settings.default_user_id))
    registry = ToolRegistry(async_session_factory, context)
    factory = build_deep_agent_factory(registry, checkpointer=checkpointer)
    return AgentRunner(factory)


def build_event_handler(agent_runner: AgentRunner) -> EventHandler:
    """Bind profile and scheduler events to the shared ``AgentRunner``."""
    return EventHandler(agent_runner=agent_runner)
