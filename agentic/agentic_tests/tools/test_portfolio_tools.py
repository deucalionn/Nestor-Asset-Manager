from decimal import Decimal

import pytest
from nam_agentic.tools.portfolio.create_index import CreateIndexTool
from nam_agentic.tools.portfolio.get_index import GetIndexTool
from nam_agentic.tools.portfolio.get_positions import GetPortfolioPositionsTool
from nam_agentic.tools.portfolio.get_user_context import GetUserContextTool
from nam_agentic.tools.portfolio.list_indices import ListIndicesTool
from nam_agentic.tools.services.market_price import FakeMarketPriceProvider
from nam_db.models.index import Index
from nam_db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from support.helpers import as_dict

pytestmark = pytest.mark.asyncio


async def test_get_user_context(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
) -> None:
    tool = GetUserContextTool(session_factory, test_user.id).as_tool()
    result = as_dict(await tool.ainvoke({}))

    assert result["user_id"] == str(test_user.id)
    assert result["strategy"] == test_user.strategy.value
    assert result["age"] >= 18


async def test_get_portfolio_positions_gain_loss_pct(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    test_index: Index,
    test_position,
) -> None:
    prices = FakeMarketPriceProvider({test_index.isin: Decimal("110")})
    tool = GetPortfolioPositionsTool(session_factory, test_user.id, prices).as_tool()
    result = as_dict(await tool.ainvoke({}))

    assert len(result["positions"]) == 1
    position = result["positions"][0]
    assert position["gain_loss_pct"] == pytest.approx(10.0)
    assert position["current_price"] == "110"
    assert result["total_market_value"] == "1100"
    assert result["total_market_value_is_complete"] is True


async def test_get_portfolio_positions_partial_total_when_price_missing(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    test_index: Index,
    test_position,
    db_session: AsyncSession,
) -> None:
    from nam_agentic.tools.services.market_price import StubMarketPriceProvider

    other = Index(name="No Price Co", isin="FR0000000001")
    db_session.add(other)
    await db_session.flush()
    from nam_db.models.position import Position

    db_session.add(
        Position(
            user_id=test_user.id,
            index_id=other.id,
            quantity=Decimal("5"),
            average_cost=Decimal("10"),
        )
    )
    await db_session.commit()

    prices = FakeMarketPriceProvider({test_index.isin: Decimal("110")})
    tool = GetPortfolioPositionsTool(session_factory, test_user.id, prices).as_tool()
    result = as_dict(await tool.ainvoke({}))

    assert len(result["positions"]) == 2
    assert result["total_market_value"] == "1100"
    assert result["total_market_value_is_complete"] is False


async def test_get_portfolio_positions_empty(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
) -> None:
    from nam_agentic.tools.services.market_price import StubMarketPriceProvider

    tool = GetPortfolioPositionsTool(
        session_factory, test_user.id, StubMarketPriceProvider()
    ).as_tool()
    result = as_dict(await tool.ainvoke({}))
    assert result["positions"] == []


async def test_create_index_upsert(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    tool = CreateIndexTool(session_factory).as_tool()
    created = as_dict(
        await tool.ainvoke(
            {"name": "Test Index", "isin": "FR0003500008", "index_type": "COMPANY"}
        )
    )
    assert created["created"] is True

    again = as_dict(
        await tool.ainvoke(
            {"name": "Other", "isin": "FR0003500008", "index_type": "COMPANY"}
        )
    )
    assert again["created"] is False
    assert again["index_id"] == created["index_id"]


async def test_get_index_by_isin(
    session_factory: async_sessionmaker[AsyncSession],
    test_index: Index,
) -> None:
    tool = GetIndexTool(session_factory).as_tool()
    result = as_dict(await tool.ainvoke({"isin": test_index.isin}))
    assert result["name"] == test_index.name


async def test_list_indices_name_search(
    session_factory: async_sessionmaker[AsyncSession],
    db_session: AsyncSession,
) -> None:
    db_session.add(Index(name="Alphabet Inc (Google)", isin="US02079K3059"))
    db_session.add(Index(name="CAC 40", isin="FR0003500008"))
    await db_session.commit()

    tool = ListIndicesTool(session_factory).as_tool()
    result = as_dict(await tool.ainvoke({"name_query": "google"}))

    assert len(result["indices"]) == 1
    assert "Google" in result["indices"][0]["name"]
