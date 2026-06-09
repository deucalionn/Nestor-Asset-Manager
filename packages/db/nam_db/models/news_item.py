from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from nam_db.base import Base
from nam_db.enums import NewsCategory, NewsSource


class NewsItem(Base):
    __tablename__ = "news_items"
    __table_args__ = (Index("ix_news_items_category_fetched_at", "category", "fetched_at"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    source: Mapped[NewsSource] = mapped_column(
        SAEnum(NewsSource, name="newssource", create_constraint=True, native_enum=True),
        nullable=False,
    )
    category: Mapped[NewsCategory] = mapped_column(
        SAEnum(NewsCategory, name="newscategory", create_constraint=True, native_enum=True),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    boursorama_ticker: Mapped[str | None] = mapped_column(String(32), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingest_run_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    content_embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
