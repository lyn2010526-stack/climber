"""add turns table

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-09-30 17:30:00.000000

`turns` is defined by the ORM (app/storage/database.py) and relied on by the
session/turn lifecycle, but no revision ever created it: databases only ever
got it through `Base.metadata.create_all`. This revision closes that gap. It is
guarded so databases that already have the table (via create_all) are untouched.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'a7b8c9d0e1f2'
down_revision: str | None = 'f1a2b3c4d5e6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = 'turns'


def _has_table() -> bool:
    return TABLE in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _has_table():
        return
    op.create_table(
        TABLE,
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('checkpoint_id', sa.String(length=36), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('iteration_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_turns_session_id'), TABLE, ['session_id'], unique=False)
    op.create_index(op.f('ix_turns_checkpoint_id'), TABLE, ['checkpoint_id'], unique=False)


def downgrade() -> None:
    if not _has_table():
        return
    op.drop_index(op.f('ix_turns_checkpoint_id'), table_name=TABLE)
    op.drop_index(op.f('ix_turns_session_id'), table_name=TABLE)
    op.drop_table(TABLE)
