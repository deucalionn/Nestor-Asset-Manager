from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nam_db.base import Base
from nam_db.enums import AgentRole, AnalysisTrigger
from nam_db.models.recommendation import recommendation_analyses

if TYPE_CHECKING:
    from nam_db.models.index import Index
    from nam_db.models.recommendation import Recommendation
    from nam_db.models.user import User


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        Index("ix_analyses_user_id_created_at", "user_id", "created_at"),
        Index(
            "ix_analyses_user_id_index_id",
            "user_id",
            "index_id",
            postgresql_where=text("index_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    agent: Mapped[AgentRole] = mapped_column(
        SAEnum(AgentRole, name="agent_enum", create_constraint=True, native_enum=True),
        nullable=False,
    )
    index_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("indices.id", ondelete="RESTRICT"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    trigger: Mapped[AnalysisTrigger] = mapped_column(
        SAEnum(
            AnalysisTrigger,
            name="analysis_trigger_enum",
            create_constraint=True,
            native_enum=True,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="analyses")
    index: Mapped[Index | None] = relationship(back_populates="analyses")
    recommendations: Mapped[list[Recommendation]] = relationship(
        secondary=recommendation_analyses,
        back_populates="analyses",
    )
