"""
add_model_settings_to_sessions

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-18 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'c3d4e5f6a7b8'
down_revision: str | None = 'b2c3d4e5f6a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _sessions_table(*, with_model_settings: bool) -> sa.Table:
    """Frozen sessions definition so batch mode works without live reflection."""
    metadata = sa.MetaData()
    columns = [
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('agent_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('context_data', sa.JSON(), nullable=False),
        sa.Column('iteration_count', sa.Integer(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    ]
    if with_model_settings:
        columns.insert(
            5,
            sa.Column('model_settings', sa.JSON(), nullable=False, server_default='{}'),
        )
    return sa.Table('sessions', metadata, *columns)


def upgrade() -> None:
    from migration_support import columns

    existing = columns('sessions')
    if 'model_settings' not in existing:
        op.add_column(
            'sessions',
            sa.Column('model_settings', sa.JSON(), nullable=False, server_default='{}'),
        )
        # DROP DEFAULT is not valid SQLite DDL; batch mode rebuilds the table so
        # the final schema matches the ORM across backends.
        with op.batch_alter_table(
            'sessions', copy_from=_sessions_table(with_model_settings=True)
        ) as batch:
            batch.alter_column('model_settings', existing_type=sa.JSON(), server_default=None)


def downgrade() -> None:
    from migration_support import columns

    if 'model_settings' in columns('sessions'):
        op.drop_column('sessions', 'model_settings')
