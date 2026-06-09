"""Revision ID: yahoo_symbol

Add yahoo_symbol to indices for Yahoo Finance ticker cache.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "yahoo_symbol"
down_revision: str | None = "news_item_embedding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("indices", sa.Column("yahoo_symbol", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("indices", "yahoo_symbol")
