"""Add memory architecture tables (L0/L1 sidecars + session archives).

Adds ``memory_sidecars`` (directory-level L0/L1 semantic sidecars, one
abstract and one overview per user-scope) and ``session_archives``
(structured session commit records with one-line summaries and memory diffs).

Revision ID: f5a6b7c8d9e0
Revises: c1d2e3f4a5b6
Create Date: 2026-10-05 08:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f5a6b7c8d9e0"
down_revision: str | Sequence[str] | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memory_sidecars",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("scope", sa.String(length=255), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("generated_by", sa.String(length=50), nullable=False, server_default="rule"),
        sa.Column("sample_note", sa.Text(), nullable=True),
        sa.Column("freshness", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.UniqueConstraint("user_id", "scope", "level", name="uq_memory_sidecar_scope_level"),
    )
    op.create_index("ix_memory_sidecars_user_id", "memory_sidecars", ["user_id"])
    op.create_index("ix_memory_sidecars_scope", "memory_sidecars", ["scope"])

    op.create_table(
        "session_archives",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("one_line_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("messages", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("memory_diff", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("archive_status", sa.String(length=20), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )
    op.create_index("ix_session_archives_user_id", "session_archives", ["user_id"])
    op.create_index("ix_session_archives_session_id", "session_archives", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_session_archives_session_id", table_name="session_archives")
    op.drop_index("ix_session_archives_user_id", table_name="session_archives")
    op.drop_table("session_archives")
    op.drop_index("ix_memory_sidecars_scope", table_name="memory_sidecars")
    op.drop_index("ix_memory_sidecars_user_id", table_name="memory_sidecars")
    op.drop_table("memory_sidecars")
