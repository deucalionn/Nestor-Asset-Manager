import pytest
from nam_agentic.context import NamRuntimeContext
from nam_agentic.tools.registry import ToolRegistry
from nam_db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.asyncio


async def test_registry_exposes_thirteen_tools(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
) -> None:
    context = NamRuntimeContext(user_id=test_user.id)
    registry = ToolRegistry(session_factory, context)
    tools = registry.all_tools()
    names = {tool.name for tool in tools}

    assert len(tools) == 13
    assert names == {
        "create_analysis",
        "create_recommendation",
        "search_past_analyses",
        "get_user_context",
        "get_portfolio_positions",
        "create_index",
        "get_index",
        "list_indices",
        "get_financials_news",
        "get_data_from_url",
        "search_boursorama",
        "get_etf_composition",
        "update_index_boursorama",
    }


async def test_registry_tool_descriptions_are_enriched(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
) -> None:
    registry = ToolRegistry(session_factory, NamRuntimeContext(user_id=test_user.id))
    for tool in registry.all_tools():
        description = tool.description or ""
        assert "Use when:" in description, tool.name
        assert "Returns:" in description, tool.name
