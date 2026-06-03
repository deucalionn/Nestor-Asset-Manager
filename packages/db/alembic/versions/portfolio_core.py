"""Revision ID: portfolio_core

Create portfolio tables: users, indices, transactions, positions.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "portfolio_core"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

strategy_enum = postgresql.ENUM(
    "CONSERVATIVE",
    "BALANCED",
    "GROWTH",
    "AGGRESSIVE",
    name="strategy_enum",
    create_type=False,
)
transaction_type_enum = postgresql.ENUM(
    "BUY",
    "SELL",
    name="transaction_type_enum",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    strategy_enum.create(op.get_bind(), checkfirst=True)
    transaction_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("firstname", sa.String(length=100), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("strategy", strategy_enum, nullable=False),
        sa.Column("goals", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "indices",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("isin", sa.String(length=12), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("isin"),
    )

    op.create_table(
        "transactions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("index_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", transaction_type_enum, nullable=False),
        sa.Column("price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fees", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("price > 0", name="ck_transactions_price_positive"),
        sa.CheckConstraint("quantity > 0", name="ck_transactions_quantity_positive"),
        sa.CheckConstraint(
            "fees IS NULL OR fees >= 0", name="ck_transactions_fees_non_negative"
        ),
        sa.ForeignKeyConstraint(["index_id"], ["indices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"], unique=False)
    op.create_index("ix_transactions_index_id", "transactions", ["index_id"], unique=False)
    op.create_index(
        "ix_transactions_user_id_date", "transactions", ["user_id", "date"], unique=False
    )
    op.create_index(
        "ix_transactions_user_id_index_id",
        "transactions",
        ["user_id", "index_id"],
        unique=False,
    )

    op.create_table(
        "positions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("index_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("average_cost", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("last_update", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_positions_quantity_non_negative"),
        sa.ForeignKeyConstraint(["index_id"], ["indices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "index_id", name="uq_positions_user_id_index_id"),
    )
    op.create_index("ix_positions_user_id", "positions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_positions_user_id", table_name="positions")
    op.drop_table("positions")
    op.drop_index("ix_transactions_user_id_index_id", table_name="transactions")
    op.drop_index("ix_transactions_user_id_date", table_name="transactions")
    op.drop_index("ix_transactions_index_id", table_name="transactions")
    op.drop_index("ix_transactions_user_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("indices")
    op.drop_table("users")
    transaction_type_enum.drop(op.get_bind(), checkfirst=True)
    strategy_enum.drop(op.get_bind(), checkfirst=True)
