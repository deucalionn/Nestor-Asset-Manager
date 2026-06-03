from datetime import UTC, datetime
from decimal import Decimal

import pytest
from factories import IndexFactory, UserFactory
from httpx import AsyncClient
from nam_api.schemas.transaction import TransactionCreate
from nam_api.services.transaction_service import TransactionService
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

    response = await async_client.get("/positions")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["index_id"] == str(index.id)
    assert body[0]["quantity"] == "3.00000000"


async def test_requires_setup_returns_404(async_client: AsyncClient) -> None:
    response = await async_client.get("/positions")
    assert response.status_code == 404
