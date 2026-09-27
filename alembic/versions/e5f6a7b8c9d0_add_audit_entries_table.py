"""add_audit_entries_table

Create ``audit_entries``, the table that makes the decision audit chain durable.

``app/core/observability/audit.py`` previously opened its own ``sqlite3``
connection (defaulting to ``:memory:``) and created its own table, bypassing the
ORM and Alembic, so every decision it recorded died with the process.  The chain
now writes through the application SQLAlchemy session onto this table, which is
what ``app/core/observability/api.py::GET /api/v1/observability/audit`` reads.

The table also enforces the append-only contract the :class:`AuditEntry`
docstring promises: ``BEFORE UPDATE`` and ``BEFORE DELETE`` triggers abort the
statement, so an entry cannot be rewritten or removed after the fact.  Triggers
are used instead of a permissions model because every writer shares one database
role.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-27 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "audit_entries"

_APPEND_ONLY_TRIGGERS = (
    (
        "trg_audit_entries_no_update",
        f"CREATE TRIGGER {TABLE}_append_only_update BEFORE UPDATE ON {TABLE} "
        "BEGIN SELECT RAISE(ABORT, 'audit_entries is append-only: UPDATE is not permitted'); END",
    ),
    (
        "trg_audit_entries_no_delete",
        f"CREATE TRIGGER {TABLE}_append_only_delete BEFORE DELETE ON {TABLE} "
        "BEGIN SELECT RAISE(ABORT, 'audit_entries is append-only: DELETE is not permitted'); END",
    ),
)


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("agent_id", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("session_id", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("decision_type", sa.String(length=100), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("output_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("alternatives_considered", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("allowed", sa.Boolean(), nullable=True),
        sa.Column("subject", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f(f"ix_{TABLE}_timestamp"), TABLE, ["timestamp"], unique=False)
    op.create_index(op.f(f"ix_{TABLE}_agent_id"), TABLE, ["agent_id"], unique=False)
    op.create_index(op.f(f"ix_{TABLE}_session_id"), TABLE, ["session_id"], unique=False)
    op.create_index(op.f(f"ix_{TABLE}_decision_type"), TABLE, ["decision_type"], unique=False)
    op.create_index(
        f"idx_{TABLE}_session_decision", TABLE, ["session_id", "decision_type"], unique=False
    )

    for _name, statement in _APPEND_ONLY_TRIGGERS:
        op.execute(sa.text(statement))


def downgrade() -> None:
    for name, _statement in _APPEND_ONLY_TRIGGERS:
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS {name}"))

    op.drop_index(f"idx_{TABLE}_session_decision", table_name=TABLE)
    op.drop_index(op.f(f"ix_{TABLE}_decision_type"), table_name=TABLE)
    op.drop_index(op.f(f"ix_{TABLE}_session_id"), table_name=TABLE)
    op.drop_index(op.f(f"ix_{TABLE}_agent_id"), table_name=TABLE)
    op.drop_index(op.f(f"ix_{TABLE}_timestamp"), table_name=TABLE)
    op.drop_table(TABLE)
