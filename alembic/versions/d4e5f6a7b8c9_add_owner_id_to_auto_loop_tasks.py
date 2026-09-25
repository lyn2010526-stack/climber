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


def upgrade() -> None:
    op.add_column(
        "auto_loop_tasks",
        sa.Column("owner_id", sa.String(length=36), nullable=False, server_default="default-user"),
    )
    op.create_index("ix_auto_loop_tasks_owner_id", "auto_loop_tasks", ["owner_id"])
    op.alter_column("auto_loop_tasks", "owner_id", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_auto_loop_tasks_owner_id", table_name="auto_loop_tasks")
    op.drop_column("auto_loop_tasks", "owner_id")
