from datetime import UTC, datetime
from decimal import Decimal

import pytest
from factories import IndexFactory, UserFactory
from httpx import AsyncClient
from nam_api.main import app
from nam_api.routers import portfolio
from nam_api.schemas.transaction import TransactionCreate
from nam_api.services.position_service import PositionService
from nam_api.services.transaction_service import TransactionService
from nam_yahoo import FakeMarketPriceProvider, StubMarketPriceProvider
from nam_db.enums import TransactionType
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def initialized_user(db_session: AsyncSession):
    user = await UserFactory.create(db_session)
    await db_session.commit()
    return user


async def test_list_positions_after_buy(
    async_client: AsyncClient, db_session: AsyncSession, initialized_user
) -> None:
    index = await IndexFactory.create(db_session)
    await db_session.commit()

    service = TransactionService()
    await service.create(
        db_session,
        initialized_user.id,
        TransactionCreate(
            index_id=index.id,
            type=TransactionType.BUY,
            price=Decimal("100"),
            quantity=Decimal("3"),
            date=datetime(2024, 1, 1, tzinfo=UTC),
        ),
    )
    await db_session.commit()

    app.dependency_overrides[portfolio.get_position_service] = lambda: PositionService(
        price_provider=StubMarketPriceProvider()
    )
    try:
        response = await async_client.get("/positions")
    finally:
        app.dependency_overrides.pop(portfolio.get_position_service, None)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["index_id"] == str(index.id)
    assert body[0]["quantity"] == "3.00000000"
    assert body[0]["current_price"] is None
    assert body[0]["gain_loss_pct"] is None


async def test_list_positions_includes_gain_loss(
    async_client: AsyncClient,
    db_session: AsyncSession,
    initialized_user,
) -> None:
    index = await IndexFactory.create(db_session, yahoo_symbol="AI.PA")
    await db_session.commit()

    tx_service = TransactionService()
    await tx_service.create(
        db_session,
        initialized_user.id,
        TransactionCreate(
            index_id=index.id,
            type=TransactionType.BUY,
            price=Decimal("100"),
            quantity=Decimal("3"),
            date=datetime(2024, 1, 1, tzinfo=UTC),
        ),
    )
    await db_session.commit()

    app.dependency_overrides[portfolio.get_position_service] = lambda: PositionService(
        price_provider=FakeMarketPriceProvider({"AI.PA": Decimal("120")})
    )
    try:
        response = await async_client.get("/positions")
    finally:
        app.dependency_overrides.pop(portfolio.get_position_service, None)

    assert response.status_code == 200
    body = response.json()[0]
    assert Decimal(body["current_price"]) == Decimal("120")
    assert Decimal(body["market_value"]) == Decimal("360")
    assert Decimal(body["unrealized_pnl"]) == Decimal("60")
    assert body["gain_loss_pct"] == pytest.approx(20.0)


async def test_requires_setup_returns_404(async_client: AsyncClient) -> None:
    response = await async_client.get("/positions")
    assert response.status_code == 404
