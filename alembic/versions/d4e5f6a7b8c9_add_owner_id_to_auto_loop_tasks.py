"""Add task ownership for API isolation.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _auto_loop_tasks_table() -> sa.Table:
    """Frozen definition for offline batch rendering."""
    metadata = sa.MetaData()
    return sa.Table(
        "auto_loop_tasks",
        metadata,
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("max_steps", sa.Integer(), nullable=False),
        sa.Column("current_step", sa.Integer(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("owner_id", sa.String(length=36), nullable=False, server_default="default-user"),
    )


def upgrade() -> None:
    op.add_column(
        "auto_loop_tasks",
        sa.Column("owner_id", sa.String(length=36), nullable=False, server_default="default-user"),
    )
    op.create_index("ix_auto_loop_tasks_owner_id", "auto_loop_tasks", ["owner_id"])
    # DROP DEFAULT is not valid SQLite DDL; batch mode rebuilds the table so the
    # final schema matches the ORM across backends.
    with op.batch_alter_table("auto_loop_tasks", copy_from=_auto_loop_tasks_table()) as batch:
        batch.alter_column("owner_id", existing_type=sa.String(length=36), server_default=None)


def downgrade() -> None:
    op.drop_index("ix_auto_loop_tasks_owner_id", table_name="auto_loop_tasks")
    op.drop_column("auto_loop_tasks", "owner_id")
