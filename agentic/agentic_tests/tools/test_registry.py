import pytest
from nam_agentic.context import NamRuntimeContext
from nam_agentic.tools.registry import ToolRegistry
from nam_db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.asyncio


async def test_registry_exposes_eight_tools(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
) -> None:
    context = NamRuntimeContext(user_id=test_user.id)
    registry = ToolRegistry(session_factory, context)
    tools = registry.all_tools()
    names = {tool.name for tool in tools}

    assert len(tools) == 8
    assert names == {
        "create_analysis",
        "create_recommendation",
        "search_past_analyses",
        "get_user_context",
        "get_portfolio_positions",
        "create_index",
        "get_index",
        "list_indices",
    }
