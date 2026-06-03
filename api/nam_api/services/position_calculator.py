from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from nam_db.enums import TransactionType

from nam_api.exceptions import InsufficientQuantityError


@dataclass(frozen=True)
class PositionSnapshot:
    quantity: Decimal
    average_cost: Decimal
    last_update: datetime


class LedgerTransaction(Protocol):
    type: TransactionType
    price: Decimal
    quantity: Decimal
    fees: Decimal | None
    date: datetime
    created_at: datetime


class PositionCalculator:
    @staticmethod
    def replay(transactions: list[LedgerTransaction]) -> PositionSnapshot | None:
        quantity = Decimal("0")
        average_cost = Decimal("0")
        last_update = datetime.now(UTC)

        for tx in transactions:
            fees = tx.fees or Decimal("0")
            last_update = tx.date

            if tx.type == TransactionType.BUY:
                total_cost = quantity * average_cost + tx.quantity * tx.price + fees
                quantity += tx.quantity
                average_cost = total_cost / quantity
            elif tx.type == TransactionType.SELL:
                if tx.quantity > quantity:
                    raise InsufficientQuantityError()
                quantity -= tx.quantity
                if quantity == 0:
                    average_cost = Decimal("0")

        if quantity == 0:
            return None

        return PositionSnapshot(
            quantity=quantity,
            average_cost=average_cost,
            last_update=last_update,
        )
