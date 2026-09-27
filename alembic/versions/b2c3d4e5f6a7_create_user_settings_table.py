"""
create_user_settings_table

Revision ID: b2c3d4e5f6a7
Revises: 52310c24d4c8
Create Date: 2026-07-28 12:45:00.000000

The original filename was ``create_user_settings_table_with_code_review_graph``
and the table carried ``enhanced_prompt_enabled`` and
``code_review_graph_enabled``.  Neither column exists on
``app/storage/models_platform.py::UserSettings`` any more, and nothing under
``app/`` or ``frontend-react/src/`` reads or writes them, so they are dropped
here rather than created and then removed.  The final state therefore matches
the ORM.

``ix_user_settings_user_id`` is dropped too: ``UserSettings.user_id`` is
``unique=True``, which already gives SQLite a unique index to serve those
lookups.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b2c3d4e5f6a7'
down_revision: str | None = '52310c24d4c8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'user_settings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('autonomous_agent_mode', sa.Boolean(), nullable=False),
        sa.Column('token_throttle_mcp_enabled', sa.Boolean(), nullable=False),
        sa.Column('mcp_status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )


def downgrade() -> None:
    op.drop_table('user_settings')
