"""Revision ID: news_ingestion

Add news_items table and extend indices with boursorama_ticker and index_type.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "news_ingestion"
down_revision: str | None = "analysis_recommendation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

newssource_enum = postgresql.ENUM("BOURSORAMA", name="newssource", create_type=False)
newscategory_enum = postgresql.ENUM(
    "CALENDAR_GENERAL",
    "CALENDAR_LISTED_COMPANIES",
    "CALENDAR_MACRO",
    "CALENDAR_DIVIDENDS",
    "MARKETS",
    "FINANCE",
    "COMPANY_NEWS",
    name="newscategory",
    create_type=False,
)
indextype_enum = postgresql.ENUM("COMPANY", "ETF", name="indextype", create_type=False)


def upgrade() -> None:
    newssource_enum.create(op.get_bind(), checkfirst=True)
    newscategory_enum.create(op.get_bind(), checkfirst=True)
    indextype_enum.create(op.get_bind(), checkfirst=True)

    op.add_column("indices", sa.Column("boursorama_ticker", sa.String(length=32), nullable=True))
    op.add_column(
        "indices",
        sa.Column(
            "index_type",
            indextype_enum,
            nullable=False,
            server_default="COMPANY",
        ),
    )

    op.create_table(
        "news_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source", newssource_enum, nullable=False),
        sa.Column("category", newscategory_enum, nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_markdown", sa.Text(), nullable=True),
        sa.Column("boursorama_ticker", sa.String(length=32), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingest_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_url"),
    )
    op.create_index(
        "ix_news_items_category_fetched_at",
        "news_items",
        ["category", "fetched_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_news_items_category_fetched_at", table_name="news_items")
    op.drop_table("news_items")
    op.drop_column("indices", "index_type")
    op.drop_column("indices", "boursorama_ticker")
    indextype_enum.drop(op.get_bind(), checkfirst=True)
    newscategory_enum.drop(op.get_bind(), checkfirst=True)
    newssource_enum.drop(op.get_bind(), checkfirst=True)
