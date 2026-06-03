from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from nam_api.exceptions import InsufficientQuantityError
from nam_api.services.position_calculator import PositionCalculator
from nam_db.enums import TransactionType


@dataclass
class Tx:
    type: TransactionType
    price: Decimal
    quantity: Decimal
    fees: Decimal | None
    date: datetime
    created_at: datetime


def _tx(
    tx_type: TransactionType,
    price: str,
    quantity: str,
    fees: str | None = None,
    *,
    day: int = 1,
) -> Tx:
    when = datetime(2024, 1, day, tzinfo=UTC)
    return Tx(
        type=tx_type,
        price=Decimal(price),
        quantity=Decimal(quantity),
        fees=Decimal(fees) if fees is not None else None,
        date=when,
        created_at=when,
    )


def test_two_buys_weighted_average_includes_fees() -> None:
    transactions = [
        _tx(TransactionType.BUY, "100", "10", "10", day=1),
        _tx(TransactionType.BUY, "120", "10", "0", day=2),
    ]

    snapshot = PositionCalculator.replay(transactions)

    assert snapshot is not None
    assert snapshot.quantity == Decimal("20")
    # (10*100 + 10 + 10*120) / 20 = 110.5
    assert snapshot.average_cost == Decimal("110.5")


def test_sell_reduces_quantity_keeps_acb() -> None:
    transactions = [
        _tx(TransactionType.BUY, "100", "10", day=1),
        _tx(TransactionType.SELL, "100", "4", day=2),
    ]

    snapshot = PositionCalculator.replay(transactions)

    assert snapshot is not None
    assert snapshot.quantity == Decimal("6")
    assert snapshot.average_cost == Decimal("100")


def test_sell_to_zero_removes_position() -> None:
    transactions = [
        _tx(TransactionType.BUY, "100", "5", day=1),
        _tx(TransactionType.SELL, "100", "5", day=2),
    ]

    assert PositionCalculator.replay(transactions) is None


def test_oversell_raises() -> None:
    transactions = [
        _tx(TransactionType.BUY, "100", "5", day=1),
        _tx(TransactionType.SELL, "100", "10", day=2),
    ]

    with pytest.raises(InsufficientQuantityError):
        PositionCalculator.replay(transactions)
