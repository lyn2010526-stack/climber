"""align_with_orm_models

Create the schema objects the ORM in ``app/storage/`` declares but no earlier
revision ever created, so that ``alembic upgrade head`` and
``Base.metadata.create_all`` (the path ``app/storage/__init__.py::init_db``
takes) converge on the same schema instead of two divergent ones.

Added here:

* table ``turns`` -- queried at runtime by ``app/core/recovery.py:89-103``
  (``select(Turn).where(Turn.session_id == ..., Turn.status == 'failed')``).
  The ``Session.turns`` relationship also cascades to it.
* 3 columns on ``agents`` (``agent_role``, ``goal``, ``backstory``) used by
  CrewAI-style agents.
* 4 columns on ``checkpoints`` holding the Pregel ``Send`` state
  (``channel_values``, ``channel_versions``, ``versions_seen``,
  ``pending_writes``).
* 1 column on ``sessions`` (``working_memory``).
* 3 columns on ``user_profiles`` (``inviolable``, ``values``, ``principles``).

All NOT NULL additions are backfilled in a first ``batch_alter_table`` pass
and have the temporary default stripped in a second pass, because SQLite
rejects ``ALTER TABLE ... ADD COLUMN ... NOT NULL`` without a default once the
target table has rows.  The end state matches the ORM: NOT NULL with no
server default.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-27 00:00:00.000000
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'd4e5f6a7b8c9'
down_revision: str | None = 'c3d4e5f6a7b8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, column, type, nullable, backfill default).  A non-None backfill is
# removed again in a second pass; see ``_add_columns``.
_ADDED_COLUMNS: tuple[tuple[str, str, object, bool, object | None], ...] = (
    ('agents', 'agent_role', sa.String(length=255), True, None),
    ('agents', 'backstory', sa.Text(), True, None),
    ('agents', 'goal', sa.Text(), True, None),
    ('checkpoints', 'channel_values', sa.Text(), False, sa.text("'{}'")),
    ('checkpoints', 'channel_versions', sa.Text(), False, sa.text("'{}'")),
    ('checkpoints', 'pending_writes', sa.Text(), False, sa.text("'[]'")),
    ('checkpoints', 'versions_seen', sa.Text(), False, sa.text("'{}'")),
    ('sessions', 'working_memory', sa.JSON(), False, sa.text("'{}'")),
    ('user_profiles', 'inviolable', sa.JSON(), False, sa.text("'[]'")),
    ('user_profiles', 'principles', sa.JSON(), False, sa.text("'[]'")),
    ('user_profiles', 'values', sa.JSON(), False, sa.text("'[]'")),
)

# (table, column) pairs the ORM declares nullable but the migrations created
# NOT NULL.  Loosening is non-destructive, and without it a caller that
# legitimately stores NULL -- ``Session.agent_id`` is ``Mapped[str | None]`` --
# gets an integrity error on an Alembic-built database while succeeding on a
# ``create_all``-built one.
_RELAXED_NULLABILITY: tuple[tuple[str, str], ...] = (
    ('agents', 'system_prompt'),
    ('sessions', 'agent_id'),
)


def _add_columns() -> None:
    """Add every column above, one recreate per table, in two passes.

    Pass 1 attaches the real definition plus, where needed, a temporary server
    default.  Pass 2 strips those temporary defaults.  The passes must stay
    separate: a single batch would create the new NOT NULL column without its
    default and then fail to copy pre-existing rows.
    """
    by_table: dict[str, list[tuple[str, str, object, bool, object | None]]] = {}
    for entry in _ADDED_COLUMNS:
        by_table.setdefault(entry[0], []).append(entry)

    for table, columns in by_table.items():
        backfilled = [column for _t, column, _ty, _n, backfill in columns if backfill is not None]
        with op.batch_alter_table(table) as batch_op:
            for _table, column, type_, nullable, backfill in columns:
                batch_op.add_column(
                    sa.Column(
                        column,
                        type_,
                        nullable=nullable,
                        server_default=backfill,
                    )
                )
        if backfilled:
            with op.batch_alter_table(table) as batch_op:
                for column in backfilled:
                    batch_op.alter_column(column, server_default=None)


def _relax_nullability() -> None:
    """Drop the NOT NULL constraint on columns the ORM marks nullable.

    SQLite has no ``ALTER COLUMN ... DROP NOT NULL``, so each change goes
    through a batch recreate, which preserves the table's indexes and foreign
    keys.
    """
    for table, column in _RELAXED_NULLABILITY:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(column, nullable=True)


def _re_tighten_nullability() -> None:
    """Re-apply NOT NULL on the way down, where it is still possible.

    NOT NULL cannot be restored once rows hold NULL in the column, and this
    migration deliberately made these two columns nullable.  Deleting or
    rewriting application rows to force the constraint back would be a worse
    outcome than leaving the column nullable, so a column that has picked up
    NULLs since the upgrade is left nullable and reported.  Re-running
    ``upgrade head`` is always safe.
    """
    for table, column in _RELAXED_NULLABILITY:
        nulls = op.get_bind().execute(
            sa.text(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NULL')
        ).scalar_one()
        if nulls:
            logging.getLogger('alembic.runtime.migration').warning(
                'downgrade %s -> %s: %d row(s) have NULL %s.%s, leaving it nullable',
                revision, down_revision, nulls, table, column,
            )
            continue
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(column, nullable=False)


def upgrade() -> None:
    op.create_table('turns',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('session_id', sa.String(length=36), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('checkpoint_id', sa.String(length=36), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('result', sa.Text(), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('iteration_count', sa.Integer(), nullable=False),
    sa.Column('tokens_used', sa.Integer(), nullable=False),
    sa.Column('metadata', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_turns_checkpoint_id'), 'turns', ['checkpoint_id'], unique=False)
    op.create_index(op.f('ix_turns_session_id'), 'turns', ['session_id'], unique=False)

    _add_columns()
    _relax_nullability()


def downgrade() -> None:
    _re_tighten_nullability()

    for table, column, _type, _nullable, _backfill in reversed(_ADDED_COLUMNS):
        op.drop_column(table, column)

    op.drop_index(op.f('ix_turns_session_id'), table_name='turns')
    op.drop_index(op.f('ix_turns_checkpoint_id'), table_name='turns')
    op.drop_table('turns')
