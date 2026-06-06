from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nam_db.base import Base

if TYPE_CHECKING:
    from nam_db.models.analysis import Analysis
    from nam_db.models.position import Position
    from nam_db.models.transaction import Transaction


class Index(Base):
    __tablename__ = "indices"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    isin: Mapped[str] = mapped_column(String(12), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    transactions: Mapped[list[Transaction]] = relationship(back_populates="index")
    positions: Mapped[list[Position]] = relationship(back_populates="index")
    analyses: Mapped[list[Analysis]] = relationship(back_populates="index")
