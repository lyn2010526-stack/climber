"""Add task ownership for API isolation.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8

Historically the DDL for auto_loop_tasks sat behind an early ``return`` in
52310c24d4c8 and never executed, so a clean database arrived here without the
table and ``add_column`` blew up with "no such table". Both paths are now
idempotent: create the full table when it is missing, otherwise only add the
ownership column.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Column list mirrors app/storage/models_platform.AutoLoopTask, minus the
# owner_id/indexes that this revision itself is responsible for.
_BASE_COLUMNS = (
    sa.Column("id", sa.String(length=36), nullable=False),
    sa.Column("objective", sa.Text(), nullable=False),
    sa.Column("status", sa.String(length=20), nullable=False),
    sa.Column("max_steps", sa.Integer(), nullable=False),
    sa.Column("current_step", sa.Integer(), nullable=False),
    sa.Column("result", sa.JSON(), nullable=True),
    sa.Column("error", sa.Text(), nullable=True),
    sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
    sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
    sa.Column("started_at", sa.DateTime(), nullable=True),
    sa.Column("finished_at", sa.DateTime(), nullable=True),
    sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
)


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector: sa.Inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "auto_loop_tasks" not in _table_names(inspector):
        op.create_table(
            "auto_loop_tasks",
            sa.Column("owner_id", sa.String(length=36), nullable=False, server_default="default-user"),
            *_BASE_COLUMNS,
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_auto_loop_tasks_owner_id", "auto_loop_tasks", ["owner_id"])
        op.create_index(op.f("ix_auto_loop_tasks_status"), "auto_loop_tasks", ["status"])
        op.create_index(op.f("ix_auto_loop_tasks_heartbeat_at"), "auto_loop_tasks", ["heartbeat_at"])
        return

    if "owner_id" in _column_names(inspector, "auto_loop_tasks"):
        return

    with op.batch_alter_table("auto_loop_tasks") as batch:
        batch.add_column(
            sa.Column("owner_id", sa.String(length=36), nullable=False, server_default="default-user"),
        )
    op.create_index("ix_auto_loop_tasks_owner_id", "auto_loop_tasks", ["owner_id"])
    with op.batch_alter_table("auto_loop_tasks") as batch:
        batch.alter_column("owner_id", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "auto_loop_tasks" not in _table_names(inspector):
        return
    if "owner_id" in _column_names(inspector, "auto_loop_tasks"):
        op.drop_index("ix_auto_loop_tasks_owner_id", table_name="auto_loop_tasks")
        with op.batch_alter_table("auto_loop_tasks") as batch:
            batch.drop_column("owner_id")
