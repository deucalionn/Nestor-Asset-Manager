from datetime import datetime
from decimal import Decimal
from uuid import UUID

from nam_db.enums import TransactionType
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TransactionCreate(BaseModel):
    index_id: UUID
    type: TransactionType
    price: Decimal = Field(gt=0)
    quantity: Decimal = Field(gt=0)
    date: datetime
    fees: Decimal | None = Field(default=None, ge=0)


class TransactionUpdate(BaseModel):
    index_id: UUID | None = None
    type: TransactionType | None = None
    price: Decimal | None = Field(default=None, gt=0)
    quantity: Decimal | None = Field(default=None, gt=0)
    date: datetime | None = None
    fees: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "TransactionUpdate":
        if not any(
            value is not None
            for value in (
                self.index_id,
                self.type,
                self.price,
                self.quantity,
                self.date,
                self.fees,
            )
        ):
            msg = "At least one field must be provided for update"
            raise ValueError(msg)
        return self


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    index_id: UUID
    type: TransactionType
    price: Decimal
    quantity: Decimal
    date: datetime
    fees: Decimal | None
    created_at: datetime
