"""create listening history table

Revision ID: b1c4e7a90d32
Revises: ab876f72af60
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b1c4e7a90d32"
down_revision: str | None = "ab876f72af60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "listening_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("track_id", sa.String(length=64), nullable=False),
        sa.Column("track_name", sa.String(length=512), nullable=False),
        sa.Column("artist_name", sa.String(length=512), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "played_at", name="uq_history_user_played_at"),
    )
    op.create_index(
        "ix_history_user_played_at",
        "listening_history",
        ["user_id", "played_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_history_user_played_at", table_name="listening_history")
    op.drop_table("listening_history")
