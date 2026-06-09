from functools import lru_cache
from uuid import UUID

from nam_db.session import async_session_factory

from nam_agentic.agent_factory import build_deep_agent_factory
from nam_agentic.context import NamRuntimeContext
from nam_agentic.runner import AgentRunner
from nam_agentic.services.event_handler import EventHandler
from nam_agentic.settings import settings
from nam_agentic.tools.registry import ToolRegistry

_default_user_id = UUID(settings.default_user_id)
_default_context = NamRuntimeContext(user_id=_default_user_id)


@lru_cache
def get_tool_registry() -> ToolRegistry:
    return ToolRegistry(async_session_factory, _default_context)


@lru_cache
def get_agent_runner() -> AgentRunner:
    registry = get_tool_registry()
    factory = build_deep_agent_factory(registry)
    return AgentRunner(factory)


event_handler = EventHandler(runner_factory=get_agent_runner)
