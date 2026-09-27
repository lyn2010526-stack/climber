"""add_task_retry_and_recovery_state

Give ``auto_loop_tasks`` the state P1-25 and P1-26 need:

* ``attempts`` / ``max_attempts`` — the retry budget of a task. A retry loop
  that keeps no counter cannot tell "failed once" from "out of budget", and a
  recovery sweep cannot tell a task that still has attempts left from one that
  has been exhausted.
* ``last_error`` — the raw text of the newest failure, kept next to ``error``
  which carries the operator-facing summary (attempt count and whether the
  failure was classified retryable or permanent).
* ``idempotency_key`` — unique, so a duplicate submission is rejected by the
  database instead of minting a second row and a second billable execution.
* ``source`` — which engine owns the row. ``app/core/task_worker.py`` and
  ``app/core/auto_loop.py`` both write this table, so recovery has to be able
  to restrict itself to its own rows. Existing rows were written by
  ``AutoLoopEngine``, hence the ``auto_loop`` default.

``attempts``, ``max_attempts`` and ``source`` are NOT NULL. SQLite rejects
``ALTER TABLE ... ADD COLUMN ... NOT NULL`` without a default once the table
has rows, so they are added with a server default in one batch pass and the
default is stripped in a second pass, exactly like
``d4e5f6a7b8c9_align_with_orm_models`` does for its NOT NULL additions. The end
state matches the ORM.

Revision ID: e6f7a8b9c0d1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-27 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'e6f7a8b9c0d1'
down_revision: str | None = 'e5f6a7b8c9d0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = 'auto_loop_tasks'

# (column, type, nullable, server_default kept in the end state)
_ADDED_COLUMNS: tuple[tuple[str, object, bool, object | None], ...] = (
    ('attempts', sa.Integer(), False, '0'),
    ('max_attempts', sa.Integer(), False, '3'),
    ('last_error', sa.Text(), True, None),
    ('idempotency_key', sa.String(length=128), True, None),
    ('source', sa.String(length=20), False, 'auto_loop'),
)

# Columns whose temporary default must be dropped again so the migration result
# matches the ORM, which declares no server default for them.
_STRIPPED_DEFAULTS: tuple[str, ...] = ('attempts', 'max_attempts', 'source')


def upgrade() -> None:
    with op.batch_alter_table(_TABLE) as batch_op:
        for column, type_, nullable, server_default in _ADDED_COLUMNS:
            batch_op.add_column(
                sa.Column(
                    column,
                    type_,
                    nullable=nullable,
                    server_default=server_default,
                )
            )
    with op.batch_alter_table(_TABLE) as batch_op:
        for column in _STRIPPED_DEFAULTS:
            batch_op.alter_column(column, server_default=None)
    # Unique so the database itself rejects a duplicate submission key. The
    # index is created separately because batch_alter_table on SQLite recreates
    # the table, and a UNIQUE column added there needs its index declared with
    # the column.
    op.create_index(
        op.f('ix_auto_loop_tasks_idempotency_key'),
        _TABLE,
        ['idempotency_key'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_auto_loop_tasks_idempotency_key'), table_name=_TABLE)
    with op.batch_alter_table(_TABLE) as batch_op:
        for column, _type, _nullable, _server_default in reversed(_ADDED_COLUMNS):
            batch_op.drop_column(column)
