from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Table, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nam_db.base import Base
from nam_db.enums import AgentRole, RecommendationStatus, RecommendationType

if TYPE_CHECKING:
    from nam_db.models.analysis import Analysis
    from nam_db.models.user import User

recommendation_analyses = Table(
    "recommendation_analyses",
    Base.metadata,
    Column(
        "recommendation_id",
        PGUUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "analysis_id",
        PGUUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (Index("ix_recommendations_user_id_status", "user_id", "status"),)

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
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[RecommendationType] = mapped_column(
        SAEnum(
            RecommendationType,
            name="recommendation_type_enum",
            create_constraint=True,
            native_enum=True,
        ),
        nullable=False,
    )
    status: Mapped[RecommendationStatus] = mapped_column(
        SAEnum(
            RecommendationStatus,
            name="recommendation_status_enum",
            create_constraint=True,
            native_enum=True,
        ),
        nullable=False,
        server_default=RecommendationStatus.PENDING.value,
    )
    user_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="recommendations")
    analyses: Mapped[list[Analysis]] = relationship(
        secondary=recommendation_analyses,
        back_populates="recommendations",
    )
