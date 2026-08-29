"""add agent_group_task execution lease columns

Revision ID: a1b2c3d4e5f6
Revises: 7f0c4d9e2a11
Create Date: 2026-08-21 10:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "7f0c4d9e2a11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("agent_group_tasks") as batch:
        batch.add_column(sa.Column("lease_owner", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("lease_token", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("lease_expires_at", sa.DateTime(), nullable=True))
    op.create_index(
        "ix_agent_group_tasks_lease_owner",
        "agent_group_tasks",
        ["lease_owner"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_group_tasks_lease_owner", table_name="agent_group_tasks")
    with op.batch_alter_table("agent_group_tasks") as batch:
        batch.drop_column("lease_expires_at")
        batch.drop_column("lease_token")
        batch.drop_column("lease_owner")
