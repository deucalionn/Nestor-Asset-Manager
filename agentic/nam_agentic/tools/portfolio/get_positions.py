from decimal import Decimal
from uuid import UUID

from langchain_core.tools import BaseTool, tool
from nam_db.models.index import Index
from nam_db.models.position import Position
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.schemas.portfolio import (
    EmptyToolInput,
    GetPortfolioPositionsOutput,
    PositionItem,
)
from nam_agentic.tools.services.market_price import MarketPriceProvider


class GetPortfolioPositionsTool(BaseNamTool):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        user_id: UUID,
        price_provider: MarketPriceProvider,
    ) -> None:
        self._session_factory = session_factory
        self._user_id = user_id
        self._price_provider = price_provider

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory
        user_id = self._user_id
        price_provider = self._price_provider

        @tool(args_schema=EmptyToolInput)
        async def get_portfolio_positions() -> GetPortfolioPositionsOutput:
            """List portfolio positions with optional gain/loss percentage."""
            async with session_factory() as session:
                stmt = (
                    select(Position)
                    .where(Position.user_id == user_id)
                    .options(selectinload(Position.index))
                    .order_by(Position.index_id)
                )
                positions = list((await session.scalars(stmt)).all())

            items: list[PositionItem] = []
            all_prices_available = bool(positions)
            total_market_value = Decimal("0")

            for position in positions:
                index: Index = position.index
                current_price = await price_provider.get_price(index.isin)
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
                    total_market_value += market_value
                else:
                    all_prices_available = False

                items.append(
                    PositionItem(
                        index_id=index.id,
                        index_name=index.name,
                        isin=index.isin,
                        quantity=position.quantity,
                        average_cost=position.average_cost,
                        last_update=position.last_update,
                        current_price=current_price,
                        market_value=market_value,
                        unrealized_pnl=unrealized_pnl,
                        gain_loss_pct=gain_loss_pct,
                    )
                )

            return GetPortfolioPositionsOutput(
                user_id=user_id,
                positions=items,
                total_market_value=total_market_value if all_prices_available else None,
            )

        return get_portfolio_positions
