"""add run_id to messages for Run lineage

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-08-28 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _inspector():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    if not _inspector().has_table("messages"):
        return
    columns = {column["name"] for column in _inspector().get_columns("messages")}
    if "run_id" in columns:
        return
    op.add_column("messages", sa.Column("run_id", sa.String(length=36), nullable=True))
    op.create_index("ix_messages_run_id", "messages", ["run_id"], unique=False)


def downgrade() -> None:
    if not _inspector().has_table("messages"):
        return
    columns = {column["name"] for column in _inspector().get_columns("messages")}
    if "run_id" not in columns:
        return
    indexes = {index["name"] for index in _inspector().get_indexes("messages")}
    if "ix_messages_run_id" in indexes:
        op.drop_index("ix_messages_run_id", table_name="messages")
    op.drop_column("messages", "run_id")
