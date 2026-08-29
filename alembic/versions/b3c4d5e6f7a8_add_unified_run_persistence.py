"""add unified Run persistence fields and durable events

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-08-28 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TURN_COLUMNS = {
    "user_id": sa.Column("user_id", sa.String(length=36), nullable=True),
    "agent_id": sa.Column("agent_id", sa.String(length=36), nullable=True),
    "kind": sa.Column("kind", sa.String(length=30), nullable=False, server_default="agent_chat"),
    "trace_id": sa.Column("trace_id", sa.String(length=36), nullable=True),
    "last_sequence": sa.Column("last_sequence", sa.Integer(), nullable=False, server_default="0"),
    "execution_token": sa.Column("execution_token", sa.Integer(), nullable=False, server_default="0"),
    "parent_run_id": sa.Column("parent_run_id", sa.String(length=36), nullable=True),
}

_TURN_INDEXES = {
    "ix_turns_user_id": ["user_id"],
    "ix_turns_agent_id": ["agent_id"],
    "ix_turns_kind": ["kind"],
    "ix_turns_trace_id": ["trace_id"],
    "ix_turns_parent_run_id": ["parent_run_id"],
}


def _inspector():
    return sa.inspect(op.get_bind())


def _ensure_turn_table() -> bool:
    """Create the missing legacy table for databases initialized by Alembic only."""
    if _inspector().has_table("turns"):
        return False

    op.create_table(
        "turns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("agent_id", sa.String(length=36), nullable=True),
        sa.Column("kind", sa.String(length=30), nullable=False, server_default="agent_chat"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("checkpoint_id", sa.String(length=36), nullable=True),
        sa.Column("trace_id", sa.String(length=36), nullable=True),
        sa.Column("last_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("execution_token", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parent_run_id", sa.String(length=36), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("iteration_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("('{}')")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    return True


def _add_missing_turn_columns() -> None:
    existing = {column["name"] for column in _inspector().get_columns("turns")}
    missing = [column for name, column in _TURN_COLUMNS.items() if name not in existing]
    if not missing:
        return
    with op.batch_alter_table("turns") as batch:
        for column in missing:
            batch.add_column(column)


def _create_missing_indexes() -> None:
    existing = {index["name"] for index in _inspector().get_indexes("turns")}
    for name, columns in _TURN_INDEXES.items():
        if name not in existing:
            op.create_index(name, "turns", columns, unique=False)


def upgrade() -> None:
    _ensure_turn_table()
    _add_missing_turn_columns()
    _create_missing_indexes()

    if _inspector().has_table("run_events"):
        return

    op.create_table(
        "run_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=True),
        sa.Column("checkpoint_id", sa.String(length=36), nullable=True),
        sa.Column("execution_token", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["run_id"], ["turns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "event_id", name="uq_run_events_run_event"),
        sa.UniqueConstraint("run_id", "sequence", name="uq_run_events_run_sequence"),
    )
    op.create_index("ix_run_events_run_id", "run_events", ["run_id"], unique=False)
    op.create_index("ix_run_events_event_type", "run_events", ["event_type"], unique=False)
    op.create_index("ix_run_events_trace_id", "run_events", ["trace_id"], unique=False)
    op.create_index("ix_run_events_checkpoint_id", "run_events", ["checkpoint_id"], unique=False)
    op.create_index("ix_run_events_run_id_sequence", "run_events", ["run_id", "sequence"], unique=False)


def downgrade() -> None:
    inspector = _inspector()
    if inspector.has_table("run_events"):
        for name in (
            "ix_run_events_run_id_sequence",
            "ix_run_events_checkpoint_id",
            "ix_run_events_trace_id",
            "ix_run_events_event_type",
            "ix_run_events_run_id",
        ):
            if name in {index["name"] for index in inspector.get_indexes("run_events")}:
                op.drop_index(name, table_name="run_events")
        op.drop_table("run_events")

    if not inspector.has_table("turns"):
        return

    existing_indexes = {index["name"] for index in inspector.get_indexes("turns")}
    for name in _TURN_INDEXES:
        if name in existing_indexes:
            op.drop_index(name, table_name="turns")

    existing_columns = {column["name"] for column in inspector.get_columns("turns")}
    removable = [name for name in _TURN_COLUMNS if name in existing_columns]
    if removable:
        with op.batch_alter_table("turns") as batch:
            for name in removable:
                batch.drop_column(name)
