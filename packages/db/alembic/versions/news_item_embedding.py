"""Revision ID: news_item_embedding

Add content_embedding to news_items for semantic search.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "news_item_embedding"
down_revision: str | None = "news_ingestion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("news_items", sa.Column("content_embedding", Vector(384), nullable=True))
    op.execute(
        "CREATE INDEX ix_news_items_content_embedding_hnsw ON news_items "
        "USING hnsw (content_embedding vector_cosine_ops) "
        "WHERE content_embedding IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_news_items_content_embedding_hnsw")
    op.drop_column("news_items", "content_embedding")
