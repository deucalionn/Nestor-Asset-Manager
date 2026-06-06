"""Revision ID: analysis_recommendation

Add analyses, recommendations, and recommendation_analyses tables.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "analysis_recommendation"
down_revision: str | None = "portfolio_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

agent_enum = postgresql.ENUM(
    "PORTFOLIO_MANAGER",
    "SECTOR_ANALYST",
    "MACRO_STRATEGIST",
    "ETF_QUANT_SPECIALIST",
    name="agent_enum",
    create_type=False,
)
recommendation_type_enum = postgresql.ENUM(
    "BUY",
    "HOLD",
    "SELL",
    name="recommendation_type_enum",
    create_type=False,
)
recommendation_status_enum = postgresql.ENUM(
    "PENDING",
    "APPLIED",
    "REJECTED",
    name="recommendation_status_enum",
    create_type=False,
)
analysis_trigger_enum = postgresql.ENUM(
    "MARKET_SESSION",
    "NEWS_EVENT",
    "MANUAL",
    "TASK",
    name="analysis_trigger_enum",
    create_type=False,
)


def upgrade() -> None:
    agent_enum.create(op.get_bind(), checkfirst=True)
    recommendation_type_enum.create(op.get_bind(), checkfirst=True)
    recommendation_status_enum.create(op.get_bind(), checkfirst=True)
    analysis_trigger_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "analyses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent", agent_enum, nullable=False),
        sa.Column("index_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_embedding", Vector(384), nullable=False),
        sa.Column("trigger", analysis_trigger_enum, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["index_id"], ["indices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analyses_user_id_created_at", "analyses", ["user_id", "created_at"], unique=False
    )
    op.create_index(
        "ix_analyses_user_id_index_id",
        "analyses",
        ["user_id", "index_id"],
        unique=False,
        postgresql_where=sa.text("index_id IS NOT NULL"),
    )
    op.execute(
        "CREATE INDEX ix_analyses_content_embedding_hnsw ON analyses "
        "USING hnsw (content_embedding vector_cosine_ops)"
    )

    op.create_table(
        "recommendations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent", agent_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("type", recommendation_type_enum, nullable=False),
        sa.Column(
            "status",
            recommendation_status_enum,
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column("user_comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recommendations_user_id_status",
        "recommendations",
        ["user_id", "status"],
        unique=False,
    )

    op.create_table(
        "recommendation_analyses",
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["recommendation_id"], ["recommendations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("recommendation_id", "analysis_id"),
    )


def downgrade() -> None:
    op.drop_table("recommendation_analyses")
    op.drop_index("ix_recommendations_user_id_status", table_name="recommendations")
    op.drop_table("recommendations")
    op.execute("DROP INDEX IF EXISTS ix_analyses_content_embedding_hnsw")
    op.drop_index("ix_analyses_user_id_index_id", table_name="analyses")
    op.drop_index("ix_analyses_user_id_created_at", table_name="analyses")
    op.drop_table("analyses")
    analysis_trigger_enum.drop(op.get_bind(), checkfirst=True)
    recommendation_status_enum.drop(op.get_bind(), checkfirst=True)
    recommendation_type_enum.drop(op.get_bind(), checkfirst=True)
    agent_enum.drop(op.get_bind(), checkfirst=True)
