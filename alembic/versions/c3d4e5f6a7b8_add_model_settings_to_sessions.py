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


def upgrade() -> None:
    conn = op.get_bind()
    existing = sa.inspect(conn).get_columns('sessions')
    if not any(column['name'] == 'model_settings' for column in existing):
        op.add_column(
            'sessions',
            sa.Column('model_settings', sa.JSON(), nullable=False, server_default='{}'),
        )
        op.alter_column('sessions', 'model_settings', server_default=None)


def downgrade() -> None:
    conn = sa.inspect(op.get_bind())
    if any(column['name'] == 'model_settings' for column in conn.get_columns('sessions')):
        op.drop_column('sessions', 'model_settings')
