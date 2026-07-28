"""
create_user_settings_table_with_code_review_graph

Revision ID: b2c3d4e5f6a7
Revises: 52310c24d4c8
Create Date: 2026-07-28 12:45:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = '52310c24d4c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_settings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('autonomous_agent_mode', sa.Boolean(), nullable=False),
        sa.Column('token_throttle_mcp_enabled', sa.Boolean(), nullable=False),
        sa.Column('enhanced_prompt_enabled', sa.Boolean(), nullable=False),
        sa.Column('code_review_graph_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('mcp_status', sa.String(length=20), nullable=False, server_default='disconnected'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_settings_user_id'), 'user_settings', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_settings_user_id'), table_name='user_settings')
    op.drop_table('user_settings')
