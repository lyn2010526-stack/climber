"""
add_enhanced_prompt_enabled_to_user_settings

Revision ID: 52310c24d4c8
Revises: dd8212a8f22a
Create Date: 2026-07-28 06:50:37.331201

The original autogenerate output for this revision carried a full copy of the
base schema. Those tables already come from dd8212a8f22a, so replaying them
fails on a fresh database (and a guard `return` used to hide that, which also
skipped the tables this revision is the only producer of). Only the genuinely
new tables are created here; every statement is guarded so databases built by
`Base.metadata.create_all` remain valid.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '52310c24d4c8'
down_revision: str | None = 'dd8212a8f22a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table('auto_loop_tasks'):
        op.create_table(
            'auto_loop_tasks',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('objective', sa.Text(), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('max_steps', sa.Integer(), nullable=False),
            sa.Column('current_step', sa.Integer(), nullable=False),
            sa.Column('result', sa.JSON(), nullable=True),
            sa.Column('error', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('finished_at', sa.DateTime(), nullable=True),
            sa.Column('heartbeat_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_auto_loop_tasks_heartbeat_at'), 'auto_loop_tasks', ['heartbeat_at'], unique=False)
        op.create_index(op.f('ix_auto_loop_tasks_status'), 'auto_loop_tasks', ['status'], unique=False)

    if not _has_table('archival_passages'):
        op.create_table(
            'archival_passages',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('text', sa.Text(), nullable=False),
            sa.Column('embedding', sa.JSON(), nullable=True),
            sa.Column('tags', sa.JSON(), nullable=False),
            sa.Column('metadata', sa.JSON(), nullable=False),
            sa.Column('archive_id', sa.String(length=36), nullable=False),
            sa.Column('access_count', sa.Integer(), nullable=False),
            sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_archival_passages_archive_id'), 'archival_passages', ['archive_id'], unique=False)
        op.create_index(op.f('ix_archival_passages_user_id'), 'archival_passages', ['user_id'], unique=False)

    if not _has_table('audit_logs'):
        op.create_table(
            'audit_logs',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('session_id', sa.String(length=36), nullable=True),
            sa.Column('user_id', sa.String(length=36), nullable=True),
            sa.Column('action', sa.String(length=50), nullable=False),
            sa.Column('severity', sa.String(length=20), nullable=False),
            sa.Column('details', sa.JSON(), nullable=False),
            sa.Column('result', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
        op.create_index(op.f('ix_audit_logs_session_id'), 'audit_logs', ['session_id'], unique=False)
        op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)

    if not _has_table('core_memory_blocks'):
        op.create_table(
            'core_memory_blocks',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('agent_id', sa.String(length=36), nullable=True),
            sa.Column('label', sa.String(length=50), nullable=False),
            sa.Column('value', sa.Text(), nullable=False),
            sa.Column('limit', sa.Integer(), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('read_only', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_core_memory_blocks_agent_id'), 'core_memory_blocks', ['agent_id'], unique=False)
        op.create_index(op.f('ix_core_memory_blocks_user_id'), 'core_memory_blocks', ['user_id'], unique=False)


def downgrade() -> None:
    if _has_table('core_memory_blocks'):
        op.drop_index(op.f('ix_core_memory_blocks_user_id'), table_name='core_memory_blocks')
        op.drop_index(op.f('ix_core_memory_blocks_agent_id'), table_name='core_memory_blocks')
        op.drop_table('core_memory_blocks')

    if _has_table('audit_logs'):
        op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
        op.drop_index(op.f('ix_audit_logs_session_id'), table_name='audit_logs')
        op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
        op.drop_table('audit_logs')

    if _has_table('archival_passages'):
        op.drop_index(op.f('ix_archival_passages_user_id'), table_name='archival_passages')
        op.drop_index(op.f('ix_archival_passages_archive_id'), table_name='archival_passages')
        op.drop_table('archival_passages')

    if _has_table('auto_loop_tasks'):
        op.drop_index(op.f('ix_auto_loop_tasks_status'), table_name='auto_loop_tasks')
        op.drop_index(op.f('ix_auto_loop_tasks_heartbeat_at'), table_name='auto_loop_tasks')
        op.drop_table('auto_loop_tasks')
