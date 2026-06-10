from decimal import Decimal
from uuid import UUID

from nam_db.models.position import Position
from nam_db.models.transaction import Transaction
from nam_db.models.user import User
from nam_db.session import async_session_factory
from nam_yahoo import MarketPriceProvider, YfinanceMarketPriceProvider
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from nam_api.exceptions import NotFoundError
from nam_api.schemas.position import PositionRead
from nam_api.services.position_calculator import PositionCalculator


def _default_price_provider() -> MarketPriceProvider:
    return YfinanceMarketPriceProvider(async_session_factory)


class PositionService:
    def __init__(
        self,
        calculator: PositionCalculator | None = None,
        price_provider: MarketPriceProvider | None = None,
    ) -> None:
        self._calculator = calculator or PositionCalculator()
        self._price_provider = (
            price_provider if price_provider is not None else _default_price_provider()
        )

    async def list_for_user(self, session: AsyncSession, user_id: UUID) -> list[PositionRead]:
        await self._ensure_user_exists(session, user_id)
        result = await session.execute(
            select(Position)
            .where(Position.user_id == user_id)
            .options(selectinload(Position.index))
            .order_by(Position.index_id)
        )
        positions = list(result.scalars().all())
        items: list[PositionRead] = []

        for position in positions:
            index = position.index
            current_price = await self._price_provider.get_price_for_index(session, index)
            market_value: Decimal | None = None
            unrealized_pnl: Decimal | None = None
            gain_loss_pct: float | None = None

            if current_price is not None:
                market_value = current_price * position.quantity
                unrealized_pnl = (current_price - position.average_cost) * position.quantity
                if position.average_cost != 0:
                    gain_loss_pct = float(
                        (current_price - position.average_cost) / position.average_cost * 100
                    )

            base = PositionRead.model_validate(position)
            items.append(
                base.model_copy(
                    update={
                        "current_price": current_price,
                        "market_value": market_value,
                        "unrealized_pnl": unrealized_pnl,
                        "gain_loss_pct": gain_loss_pct,
                    }
                )
            )

        return items

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
