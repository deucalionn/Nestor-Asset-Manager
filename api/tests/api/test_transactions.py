from decimal import Decimal

import pytest
from factories import IndexFactory, UserFactory
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def initialized_user(db_session: AsyncSession):
    user = await UserFactory.create(db_session)
    await db_session.commit()
    return user


async def test_create_and_list_transactions(
    async_client: AsyncClient, db_session: AsyncSession, initialized_user
) -> None:
    index = await IndexFactory.create(db_session)
    await db_session.commit()

    response = await async_client.post(
        "/transactions",
        json={
            "index_id": str(index.id),
            "type": "BUY",
            "price": "100",
            "quantity": "5",
            "date": "2024-01-01T00:00:00Z",
            "fees": "2.5",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == str(initialized_user.id)
    assert body["type"] == "BUY"

    list_response = await async_client.get("/transactions")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


async def test_insufficient_sell_returns_422(
    async_client: AsyncClient, db_session: AsyncSession, initialized_user
) -> None:
    index = await IndexFactory.create(db_session)
    await db_session.commit()

    response = await async_client.post(
        "/transactions",
        json={
            "index_id": str(index.id),
            "type": "SELL",
            "price": "100",
            "quantity": "1",
            "date": "2024-01-01T00:00:00Z",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Insufficient quantity for SELL transaction"


async def test_update_transaction(
    async_client: AsyncClient, db_session: AsyncSession, initialized_user
) -> None:
    index = await IndexFactory.create(db_session)
    await db_session.commit()

    create_response = await async_client.post(
        "/transactions",
        json={
            "index_id": str(index.id),
            "type": "BUY",
            "price": "100",
            "quantity": "5",
            "date": "2024-01-01T00:00:00Z",
        },
    )
    tx_id = create_response.json()["id"]

    update_response = await async_client.put(
        f"/transactions/{tx_id}",
        json={"price": "150"},
    )

    assert update_response.status_code == 200
    assert Decimal(update_response.json()["price"]) == Decimal("150")


async def test_delete_transaction(
    async_client: AsyncClient, db_session: AsyncSession, initialized_user
) -> None:
    index = await IndexFactory.create(db_session)
    await db_session.commit()

    create_response = await async_client.post(
        "/transactions",
        json={
            "index_id": str(index.id),
            "type": "BUY",
            "price": "100",
            "quantity": "5",
            "date": "2024-01-01T00:00:00Z",
        },
    )
    tx_id = create_response.json()["id"]

    delete_response = await async_client.delete(f"/transactions/{tx_id}")
    assert delete_response.status_code == 204

    list_response = await async_client.get("/transactions")
    assert list_response.json() == []


async def test_requires_setup_returns_404(async_client: AsyncClient) -> None:
    response = await async_client.get("/transactions")
    assert response.status_code == 404
    assert "setup" in response.json()["detail"].lower()
