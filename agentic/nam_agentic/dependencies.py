from functools import lru_cache
from uuid import UUID

from nam_agentic.context import NamRuntimeContext
from nam_agentic.services.event_handler import EventHandler
from nam_agentic.settings import settings
from nam_agentic.tools.registry import ToolRegistry
from nam_db.session import async_session_factory

_default_user_id = UUID(settings.default_user_id)
_default_context = NamRuntimeContext(user_id=_default_user_id)

event_handler = EventHandler()


@lru_cache
def get_tool_registry() -> ToolRegistry:
    return ToolRegistry(async_session_factory, _default_context)
