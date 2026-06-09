import pytest
from nam_agentic.context import NamRuntimeContext
from nam_agentic.tools.registry import ToolRegistry
from nam_agentic.tools.services.market_price import StubMarketPriceProvider
from nam_db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.asyncio


async def test_registry_exposes_nineteen_tools(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
) -> None:
    context = NamRuntimeContext(user_id=test_user.id)
    registry = ToolRegistry(
        session_factory,
        context,
        price_provider=StubMarketPriceProvider(),
    )
    tools = registry.all_tools()
    names = {tool.name for tool in tools}

    assert len(tools) == 19
    assert names == {
        "create_analysis",
        "create_recommendation",
        "search_past_analyses",
        "get_user_context",
        "get_portfolio_positions",
        "create_index",
        "get_index",
        "list_indices",
        "get_financials_news_from_bourso",
        "get_data_from_url",
        "search_boursorama",
        "get_etf_composition",
        "update_index_boursorama",
        "get_asset_price_from_yf",
        "get_asset_history_from_yf",
        "get_company_financials_from_yf",
        "get_asset_news_from_yf",
        "search_yahoo_symbol",
        "update_index_yahoo_symbol",
    }
    assert "get_financials_news" not in names


async def test_registry_tool_descriptions_are_enriched(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
) -> None:
    registry = ToolRegistry(
        session_factory,
        NamRuntimeContext(user_id=test_user.id),
        price_provider=StubMarketPriceProvider(),
    )
    for tool in registry.all_tools():
        description = tool.description or ""
        assert "Use when:" in description, tool.name
        assert "Returns:" in description, tool.name
