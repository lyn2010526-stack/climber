"""
add user profile tables

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-10-01 10:00:00.000000

Two tables behind the persisted profile loop: user_profile_events (append-only
Agent-internal interaction signals) and user_profile_snapshots (one summary
projection per user). Both are guarded so create_all-built databases are
untouched, and the definitions are frozen here rather than read from the ORM.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: str | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EVENTS = "user_profile_events"
SNAPSHOTS = "user_profile_snapshots"


def _has_table(name: str) -> bool:
    from migration_support import has_table

    return has_table(name)


def upgrade() -> None:
    if not _has_table(EVENTS):
        op.create_table(
            EVENTS,
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("task_type", sa.String(length=128), nullable=False),
            sa.Column("tool", sa.String(length=128), nullable=True),
            sa.Column("reasoning_level", sa.String(length=32), nullable=False),
            sa.Column("outcome", sa.String(length=16), nullable=False),
            sa.Column("feedback", sa.String(length=16), nullable=True),
            sa.Column("interrupted", sa.Boolean(), nullable=False),
            sa.Column("retried", sa.Boolean(), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.CheckConstraint(
                "source IN ('agent_internal', 'instruction_trace')",
                name="ck_user_profile_events_source",
            ),
            sa.CheckConstraint(
                "outcome IN ('success', 'failure')",
                name="ck_user_profile_events_outcome",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_user_profile_events_user_id"), EVENTS, ["user_id"], unique=False)

    if not _has_table(SNAPSHOTS):
        op.create_table(
            SNAPSHOTS,
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("user_id"),
        )


def downgrade() -> None:
    if _has_table(SNAPSHOTS):
        op.drop_table(SNAPSHOTS)
    if _has_table(EVENTS):
        op.drop_index(op.f("ix_user_profile_events_user_id"), table_name=EVENTS)
        op.drop_table(EVENTS)
