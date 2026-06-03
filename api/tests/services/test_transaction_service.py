from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from factories import IndexFactory, UserFactory
from nam_api.exceptions import InsufficientQuantityError, NotFoundError
from nam_api.schemas.transaction import TransactionCreate, TransactionUpdate
from nam_api.services.transaction_service import TransactionService
from nam_db.enums import TransactionType
from nam_db.models.position import Position
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def service() -> TransactionService:
    return TransactionService()


async def test_create_buy_updates_position(
    db_session: AsyncSession, service: TransactionService
) -> None:
    user = await UserFactory.create(db_session)
    index = await IndexFactory.create(db_session)
    await db_session.commit()

    tx = await service.create(
        db_session,
        user.id,
        TransactionCreate(
            index_id=index.id,
            type=TransactionType.BUY,
            price=Decimal("100"),
            quantity=Decimal("10"),
            date=datetime(2024, 1, 1, tzinfo=UTC),
            fees=Decimal("5"),
        ),
    )

    positions = (
        await db_session.execute(select(Position).where(Position.user_id == user.id))
    ).scalars().all()

    assert tx.user_id == user.id
    assert len(positions) == 1
    assert positions[0].quantity == Decimal("10")
    assert positions[0].average_cost == Decimal("100.5")


async def test_create_sell_insufficient_quantity(
    db_session: AsyncSession, service: TransactionService
) -> None:
    user = await UserFactory.create(db_session)
    index = await IndexFactory.create(db_session)
    await db_session.commit()

    with pytest.raises(InsufficientQuantityError):
        await service.create(
            db_session,
            user.id,
            TransactionCreate(
                index_id=index.id,
                type=TransactionType.SELL,
                price=Decimal("100"),
                quantity=Decimal("1"),
                date=datetime(2024, 1, 1, tzinfo=UTC),
            ),
        )


async def test_update_recalculates_position(
    db_session: AsyncSession, service: TransactionService
) -> None:
    user = await UserFactory.create(db_session)
    index = await IndexFactory.create(db_session)
    await db_session.commit()

    tx = await service.create(
        db_session,
        user.id,
        TransactionCreate(
            index_id=index.id,
            type=TransactionType.BUY,
            price=Decimal("100"),
            quantity=Decimal("10"),
            date=datetime(2024, 1, 1, tzinfo=UTC),
        ),
    )

    updated = await service.update(
        db_session,
        user.id,
        tx.id,
        TransactionUpdate(price=Decimal("200")),
    )

    position = (
        await db_session.execute(
            select(Position).where(
                Position.user_id == user.id, Position.index_id == index.id
            )
        )
    ).scalar_one()

    assert updated.price == Decimal("200")
    assert position.average_cost == Decimal("200")


async def test_delete_recalculates_position(
    db_session: AsyncSession, service: TransactionService
) -> None:
    user = await UserFactory.create(db_session)
    index = await IndexFactory.create(db_session)
    await db_session.commit()

    tx = await service.create(
        db_session,
        user.id,
        TransactionCreate(
            index_id=index.id,
            type=TransactionType.BUY,
            price=Decimal("100"),
            quantity=Decimal("10"),
            date=datetime(2024, 1, 1, tzinfo=UTC),
        ),
    )

    await service.delete(db_session, user.id, tx.id)

    positions = (
        await db_session.execute(select(Position).where(Position.user_id == user.id))
    ).scalars().all()
    assert positions == []


async def test_unknown_user(db_session: AsyncSession, service: TransactionService) -> None:
    index = await IndexFactory.create(db_session)
    await db_session.commit()

    with pytest.raises(NotFoundError):
        await service.create(
            db_session,
            uuid4(),
            TransactionCreate(
                index_id=index.id,
                type=TransactionType.BUY,
                price=Decimal("100"),
                quantity=Decimal("1"),
                date=datetime(2024, 1, 1, tzinfo=UTC),
            ),
        )
