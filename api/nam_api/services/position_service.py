from uuid import UUID

from nam_db.models.position import Position
from nam_db.models.transaction import Transaction
from nam_db.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nam_api.exceptions import NotFoundError
from nam_api.schemas.position import PositionRead
from nam_api.services.position_calculator import PositionCalculator


class PositionService:
    def __init__(self, calculator: PositionCalculator | None = None) -> None:
        self._calculator = calculator or PositionCalculator()

    async def list_for_user(self, session: AsyncSession, user_id: UUID) -> list[PositionRead]:
        await self._ensure_user_exists(session, user_id)
        result = await session.execute(
            select(Position)
            .where(Position.user_id == user_id)
            .order_by(Position.index_id)
        )
        return [PositionRead.model_validate(row) for row in result.scalars().all()]

    async def recalculate_for_user_index(
        self, session: AsyncSession, user_id: UUID, index_id: UUID
    ) -> None:
        result = await session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id, Transaction.index_id == index_id)
            .order_by(Transaction.date, Transaction.created_at)
        )
        transactions = list(result.scalars().all())
        snapshot = self._calculator.replay(transactions)

        existing = await session.execute(
            select(Position).where(
                Position.user_id == user_id, Position.index_id == index_id
            )
        )
        position = existing.scalar_one_or_none()

        if snapshot is None:
            if position is not None:
                await session.delete(position)
            return

        if position is None:
            session.add(
                Position(
                    user_id=user_id,
                    index_id=index_id,
                    quantity=snapshot.quantity,
                    average_cost=snapshot.average_cost,
                    last_update=snapshot.last_update,
                )
            )
        else:
            position.quantity = snapshot.quantity
            position.average_cost = snapshot.average_cost
            position.last_update = snapshot.last_update

    async def _ensure_user_exists(self, session: AsyncSession, user_id: UUID) -> None:
        user = await session.get(User, user_id)
        if user is None:
            raise NotFoundError("User not found")
