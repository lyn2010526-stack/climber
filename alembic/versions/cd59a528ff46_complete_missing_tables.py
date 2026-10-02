"""Complete the missing tables.

Revision ID: cd59a528ff46
Revises: e5f6a7b8c9d0
Create Date: 2026-10-02 06:17:17.206419

Autogenerate output trimmed to the 12 ORM tables the migration chain never
created (turns, user_sessions, user_invitations, user_activities,
user_preferences, auth_api_keys, core_memory_blocks, archival_passages,
audit_logs, personas, session_personas, lifecycle_memories); auto_loop_tasks
is the 13th and is created by d4e5f6a7b8c9. Column drift on existing tables
and the unnamed drop_constraint directives were dropped: they fail as
rendered and belong to separate findings, not to a fresh-DB bootstrap.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'cd59a528ff46'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('archival_passages',
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
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_archival_passages_archive_id'), 'archival_passages', ['archive_id'], unique=False)
    op.create_index(op.f('ix_archival_passages_user_id'), 'archival_passages', ['user_id'], unique=False)
    op.create_table('audit_logs',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('session_id', sa.String(length=36), nullable=True),
    sa.Column('user_id', sa.String(length=36), nullable=True),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('severity', sa.String(length=20), nullable=False),
    sa.Column('details', sa.JSON(), nullable=False),
    sa.Column('result', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_session_id'), 'audit_logs', ['session_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_table('auth_api_keys',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('key_hash', sa.String(length=128), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.Column('owner', sa.String(length=64), nullable=False),
    sa.Column('scopes', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('last_used_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_auth_api_keys_key_hash'), 'auth_api_keys', ['key_hash'], unique=True)
    op.create_index(op.f('ix_auth_api_keys_owner'), 'auth_api_keys', ['owner'], unique=False)
    op.create_table('lifecycle_memories',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('agent_id', sa.String(length=36), nullable=True),
    sa.Column('content', sa.String(length=4000), nullable=False),
    sa.Column('memory_type', sa.String(length=50), nullable=False),
    sa.Column('importance', sa.Float(), nullable=False),
    sa.Column('is_archived', sa.Boolean(), nullable=False),
    sa.Column('is_forgotten', sa.Boolean(), nullable=False),
    sa.Column('days_since_access', sa.Integer(), nullable=False),
    sa.Column('access_count', sa.Integer(), nullable=False),
    sa.Column('metadata', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
    sa.Column('archived_at', sa.DateTime(), nullable=True),
    sa.Column('forgotten_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lifecycle_memories_agent_id'), 'lifecycle_memories', ['agent_id'], unique=False)
    op.create_index(op.f('ix_lifecycle_memories_user_id'), 'lifecycle_memories', ['user_id'], unique=False)
    op.create_table('personas',
    sa.Column('agent_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=255), nullable=False),
    sa.Column('personality_traits', sa.JSON(), nullable=False),
    sa.Column('expertise', sa.JSON(), nullable=False),
    sa.Column('communication_style', sa.String(length=500), nullable=False),
    sa.Column('goals', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.String(length=50), nullable=False),
    sa.Column('updated_at', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('agent_id')
    )
    op.create_table('session_personas',
    sa.Column('session_id', sa.String(length=36), nullable=False),
    sa.Column('base_persona_id', sa.String(length=36), nullable=False),
    sa.Column('overrides', sa.JSON(), nullable=False),
    sa.Column('learnings', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('session_id')
    )
    op.create_index(op.f('ix_session_personas_base_persona_id'), 'session_personas', ['base_persona_id'], unique=False)
    op.create_table('user_activities',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('resource_type', sa.String(length=64), nullable=True),
    sa.Column('resource_id', sa.String(length=128), nullable=True),
    sa.Column('ip_address', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=512), nullable=True),
    sa.Column('metadata_json', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_activities_user_id'), 'user_activities', ['user_id'], unique=False)
    op.create_table('user_invitations',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('email', sa.String(length=256), nullable=False),
    sa.Column('token_hash', sa.String(length=128), nullable=False),
    sa.Column('invited_by', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=32), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('accepted_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index(op.f('ix_user_invitations_email'), 'user_invitations', ['email'], unique=False)
    op.create_table('user_preferences',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=128), nullable=False),
    sa.Column('value', sa.Text(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_preferences_user_id'), 'user_preferences', ['user_id'], unique=False)
    op.create_table('user_sessions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=128), nullable=False),
    sa.Column('refresh_token_hash', sa.String(length=128), nullable=True),
    sa.Column('ip_address', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=512), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('refresh_token_hash'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)
    op.create_table('core_memory_blocks',
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
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_core_memory_blocks_agent_id'), 'core_memory_blocks', ['agent_id'], unique=False)
    op.create_index(op.f('ix_core_memory_blocks_user_id'), 'core_memory_blocks', ['user_id'], unique=False)
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


def downgrade() -> None:
    op.drop_index(op.f('ix_turns_session_id'), table_name='turns')
    op.drop_index(op.f('ix_turns_checkpoint_id'), table_name='turns')
    op.drop_table('turns')
    op.drop_index(op.f('ix_core_memory_blocks_user_id'), table_name='core_memory_blocks')
    op.drop_index(op.f('ix_core_memory_blocks_agent_id'), table_name='core_memory_blocks')
    op.drop_table('core_memory_blocks')
    op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
    op.drop_table('user_sessions')
    op.drop_index(op.f('ix_user_preferences_user_id'), table_name='user_preferences')
    op.drop_table('user_preferences')
    op.drop_index(op.f('ix_user_invitations_email'), table_name='user_invitations')
    op.drop_table('user_invitations')
    op.drop_index(op.f('ix_user_activities_user_id'), table_name='user_activities')
    op.drop_table('user_activities')
    op.drop_index(op.f('ix_session_personas_base_persona_id'), table_name='session_personas')
    op.drop_table('session_personas')
    op.drop_table('personas')
    op.drop_index(op.f('ix_lifecycle_memories_user_id'), table_name='lifecycle_memories')
    op.drop_index(op.f('ix_lifecycle_memories_agent_id'), table_name='lifecycle_memories')
    op.drop_table('lifecycle_memories')
    op.drop_index(op.f('ix_auth_api_keys_owner'), table_name='auth_api_keys')
    op.drop_index(op.f('ix_auth_api_keys_key_hash'), table_name='auth_api_keys')
    op.drop_table('auth_api_keys')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_session_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_archival_passages_user_id'), table_name='archival_passages')
    op.drop_index(op.f('ix_archival_passages_archive_id'), table_name='archival_passages')
    op.drop_table('archival_passages')
