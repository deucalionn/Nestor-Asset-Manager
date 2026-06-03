from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nam_db.base import Base
from nam_db.enums import TransactionType

if TYPE_CHECKING:
    from nam_db.models.index import Index
    from nam_db.models.user import User


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_transactions_price_positive"),
        CheckConstraint("quantity > 0", name="ck_transactions_quantity_positive"),
        CheckConstraint("fees IS NULL OR fees >= 0", name="ck_transactions_fees_non_negative"),
        Index("ix_transactions_user_id", "user_id"),
        Index("ix_transactions_index_id", "index_id"),
        Index("ix_transactions_user_id_date", "user_id", "date"),
        Index("ix_transactions_user_id_index_id", "user_id", "index_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    index_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("indices.id", ondelete="RESTRICT"), nullable=False
    )
    type: Mapped[TransactionType] = mapped_column(
        SAEnum(
            TransactionType,
            name="transaction_type_enum",
            create_constraint=True,
            native_enum=True,
        ),
        nullable=False,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fees: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="transactions")
    index: Mapped[Index] = relationship(back_populates="transactions")
