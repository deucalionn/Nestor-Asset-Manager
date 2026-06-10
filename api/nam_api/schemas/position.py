from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    index_id: UUID
    quantity: Decimal
    average_cost: Decimal
    last_update: datetime
    current_price: Decimal | None = None
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    gain_loss_pct: float | None = Field(
        default=None,
        description="Unrealized gain/loss vs average cost, in percent (e.g. 12.5 = +12.5%).",
    )
