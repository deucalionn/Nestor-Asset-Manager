from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from nam_db.enums import Strategy
from pydantic import BaseModel, ConfigDict, Field, model_validator


class EmptyToolInput(BaseModel):
    """No LLM-visible arguments — runtime user_id is injected at bind time."""


class UserContextOutput(BaseModel):
    user_id: UUID
    firstname: str
    date_of_birth: date
    age: int
    strategy: Strategy
    goals: str


class PositionItem(BaseModel):
    index_id: UUID
    index_name: str
    isin: str
    quantity: Decimal
    average_cost: Decimal
    last_update: datetime
    current_price: Decimal | None = None
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    gain_loss_pct: float | None = None


class GetPortfolioPositionsOutput(BaseModel):
    user_id: UUID
    positions: list[PositionItem]
    total_market_value: Decimal | None = None


class CreateIndexInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    isin: str = Field(min_length=1, max_length=12)


class CreateIndexOutput(BaseModel):
    index_id: UUID
    name: str
    isin: str
    created: bool


class GetIndexInput(BaseModel):
    index_id: UUID | None = None
    isin: str | None = None

    @model_validator(mode="after")
    def exactly_one_identifier(self) -> "GetIndexInput":
        has_id = self.index_id is not None
        has_isin = self.isin is not None
        if has_id == has_isin:
            msg = "Exactly one of index_id or isin must be provided"
            raise ValueError(msg)
        return self


class IndexDetailOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index_id: UUID = Field(validation_alias="id")
    name: str
    isin: str
    created_at: datetime


class ListIndicesInput(BaseModel):
    name_query: str | None = None


class IndexListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index_id: UUID = Field(validation_alias="id")
    name: str
    isin: str
    created_at: datetime


class ListIndicesOutput(BaseModel):
    indices: list[IndexListItem]
