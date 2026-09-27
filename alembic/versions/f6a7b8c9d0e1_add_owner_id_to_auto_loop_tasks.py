"""add persisted ownership to auto loop tasks

Revision ID: f6a7b8c9d0e1
Revises: e4f5a6b7c8d9
Create Date: 2026-09-26 00:00:00.000000
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    if not inspector.has_table("auto_loop_tasks"):
        return

    columns = {column["name"] for column in inspector.get_columns("auto_loop_tasks")}
    if "owner_id" not in columns:
        op.add_column("auto_loop_tasks", sa.Column("owner_id", sa.String(length=36), nullable=True))

    indexes = {index["name"] for index in inspect(connection).get_indexes("auto_loop_tasks")}
    if "ix_auto_loop_tasks_owner_id" not in indexes:
        op.create_index("ix_auto_loop_tasks_owner_id", "auto_loop_tasks", ["owner_id"], unique=False)

    # Preserve the existing JSON-based ownership convention where it is
    # unambiguous. Rows without that field remain nullable for later repair.
    rows = connection.execute(
        sa.text("SELECT id, objective FROM auto_loop_tasks WHERE owner_id IS NULL")
    ).mappings()
    for row in rows:
        try:
            payload = json.loads(row["objective"])
        except (TypeError, json.JSONDecodeError):
            continue
        owner_id = payload.get("_owner_id") if isinstance(payload, dict) else None
        if owner_id:
            connection.execute(
                sa.text("UPDATE auto_loop_tasks SET owner_id = :owner_id WHERE id = :task_id"),
                {"owner_id": str(owner_id), "task_id": row["id"]},
            )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    if not inspector.has_table("auto_loop_tasks"):
        return

    indexes = {index["name"] for index in inspector.get_indexes("auto_loop_tasks")}
    if "ix_auto_loop_tasks_owner_id" in indexes:
        op.drop_index("ix_auto_loop_tasks_owner_id", table_name="auto_loop_tasks")

    # Keep the column on downgrade so persisted ownership values are never
    # destroyed. A later explicit cleanup migration can remove it safely.
