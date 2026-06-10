import pytest
from nam_agentic.agents.etf_quant import EtfQuantSpecialistAgent
from nam_agentic.agents.macro_strategist import MacroStrategistAgent
from nam_agentic.agents.portfolio_manager import PortfolioManagerAgent
from nam_agentic.agents.sector_analyst import SectorAnalystAgent
from nam_agentic.context import NamRuntimeContext
from nam_agentic.tools.registry import ToolRegistry
from nam_agentic.tools.services.market_price import StubMarketPriceProvider
from nam_db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.asyncio


def _tool_names(tools) -> set[str]:
    return {tool.name for tool in tools}


async def test_portfolio_manager_tools(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
) -> None:
    registry = ToolRegistry(
        session_factory,
        NamRuntimeContext(user_id=test_user.id),
        price_provider=StubMarketPriceProvider(),
    )
    pm = PortfolioManagerAgent(registry)

    assert _tool_names(pm.tools()) == {
        "get_user_context",
        "get_portfolio_positions",
        "search_past_analyses",
        "list_indices",
        "get_index",
        "create_index",
        "create_recommendation",
        "fetch_calendar_from_bourso",
        "get_financials_news_from_bourso",
        "get_asset_news_from_yf",
        "search_boursorama",
        "get_data_from_url",
    }


async def test_subagent_tools(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
) -> None:
    registry = ToolRegistry(
        session_factory,
        NamRuntimeContext(user_id=test_user.id),
        price_provider=StubMarketPriceProvider(),
    )

    macro = MacroStrategistAgent(registry)
    assert _tool_names(macro.tools()) == {
        "create_analysis",
        "search_past_analyses",
        "get_financials_news_from_bourso",
        "get_data_from_url",
        "get_asset_price_from_yf",
        "get_asset_history_from_yf",
        "get_asset_news_from_yf",
    }

    sector = SectorAnalystAgent(registry)
    assert _tool_names(sector.tools()) == {
        "create_analysis",
        "search_past_analyses",
        "get_financials_news_from_bourso",
        "get_data_from_url",
        "search_boursorama",
        "update_index_boursorama",
        "get_index",
        "get_portfolio_positions",
        "get_asset_price_from_yf",
        "get_asset_history_from_yf",
        "get_asset_news_from_yf",
        "get_company_financials_from_yf",
        "search_yahoo_symbol",
        "update_index_yahoo_symbol",
    }

    etf = EtfQuantSpecialistAgent(registry)
    assert _tool_names(etf.tools()) == {
        "create_analysis",
        "search_past_analyses",
        "get_financials_news_from_bourso",
        "get_data_from_url",
        "search_boursorama",
        "update_index_boursorama",
        "get_index",
        "get_portfolio_positions",
        "get_etf_composition",
        "get_asset_price_from_yf",
        "get_asset_history_from_yf",
        "get_asset_news_from_yf",
    }
    assert "fetch_calendar_from_bourso" not in _tool_names(macro.tools())
    assert "fetch_calendar_from_bourso" not in _tool_names(sector.tools())
    assert "fetch_calendar_from_bourso" not in _tool_names(etf.tools())
