"""add checkpoint query indexes

Revision ID: e4f5a6b7c8d9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-26 00:00:00.000000
"""

from collections.abc import Sequence

from sqlalchemy import inspect

from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_INDEXES = (
    (
        "ix_checkpoints_session_thread_iteration_created",
        ["session_id", "thread_id", "iteration", "created_at"],
    ),
    (
        "ix_checkpoints_session_thread_created",
        ["session_id", "thread_id", "created_at"],
    ),
    ("ix_checkpoints_session_created", ["session_id", "created_at"]),
)


def upgrade() -> None:
    connection = op.get_bind()
    # ``checkpoints`` is created by the application bootstrap (``create_all``) on
    # databases that already exist, so this migration only owns the indexes.
    if not inspect(connection).has_table("checkpoints"):
        return
    existing = {index["name"] for index in inspect(connection).get_indexes("checkpoints")}
    for name, columns in _INDEXES:
        if name not in existing:
            op.create_index(name, "checkpoints", columns, unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    if not inspect(connection).has_table("checkpoints"):
        return
    existing = {index["name"] for index in inspect(connection).get_indexes("checkpoints")}
    for name, _columns in reversed(_INDEXES):
        if name in existing:
            op.drop_index(name, table_name="checkpoints")
