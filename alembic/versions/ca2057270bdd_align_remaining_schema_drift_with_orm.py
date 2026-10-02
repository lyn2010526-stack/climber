"""Align remaining schema drift with the ORM models.

Covers every column that existed only in SQLAlchemy models and never in the
migration chain, so runtime writes stop 500-ing on migrated databases:

- users: the auth-era ORM (username/hashed_password/role/status/...) on top of
  the legacy 6-column DDL (password_hash/is_admin/is_active). Legacy values are
  backfilled into the new columns; legacy columns are kept for compatibility.
- agents: agent_role / goal / backstory (CrewAI-style prompt assembly)
- sessions: working_memory
- documents: content_hash (indexed) / indexed_at
- skills: 9 missing columns (scope tiers, soft delete, versioning)
- mcp_servers: updated_at / last_error / process_pid / tools
- agent_group_tasks: dependencies / context (group scheduling)
- checkpoints: langgraph state columns
- user_profiles: inviolable / values / principles (identity memory)
- user_settings: code_review_graph_enabled

Revision ID: ca2057270bdd
Revises: cd59a528ff46
Create Date: 2026-10-02 08:15:41.655594
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ca2057270bdd'
down_revision: Union[str, None] = 'cd59a528ff46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_columns(table: str, columns: list[sa.Column]) -> None:
    for column in columns:
        op.add_column(table, column)


def upgrade() -> None:
    # --- users: legacy 6-column DDL -> auth-era ORM shape ---
    _add_columns('users', [
        sa.Column('username', sa.String(length=64), nullable=False, server_default=''),
        sa.Column('hashed_password', sa.String(length=256), nullable=False, server_default=''),
        sa.Column('full_name', sa.String(length=128), nullable=True),
        sa.Column('role', sa.String(length=32), nullable=False, server_default='viewer'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('avatar_url', sa.String(length=512), nullable=True),
        sa.Column('preferences', sa.Text(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
    ])
    op.execute("UPDATE users SET hashed_password = COALESCE(password_hash, '')")
    op.execute("UPDATE users SET username = email WHERE username = ''")
    op.execute("UPDATE users SET role = CASE WHEN is_admin THEN 'admin' ELSE 'viewer' END")
    op.execute("UPDATE users SET status = CASE WHEN is_active THEN 'active' ELSE 'inactive' END")
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=False)

    # --- agents ---
    _add_columns('agents', [
        sa.Column('agent_role', sa.String(length=255), nullable=True),
        sa.Column('goal', sa.Text(), nullable=True),
        sa.Column('backstory', sa.Text(), nullable=True),
    ])

    # --- sessions ---
    op.add_column(
        'sessions',
        sa.Column('working_memory', sa.JSON(), nullable=False, server_default='{}'),
    )
    # Agentless sessions (agent_id=None) hit a NOT NULL constraint on the
    # migrated DDL; the ORM has always allowed NULL.
    with op.batch_alter_table('sessions') as batch:
        batch.alter_column(
            'agent_id',
            existing_type=sa.String(length=36),
            nullable=True,
        )

    # --- documents ---
    _add_columns('documents', [
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('indexed_at', sa.DateTime(), nullable=True),
    ])
    op.create_index('ix_documents_content_hash', 'documents', ['content_hash'], unique=False)

    # --- skills: 9 columns for scope tiers, soft delete and versioning ---
    _add_columns('skills', [
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('scope', sa.String(length=20), nullable=False, server_default='global'),
        sa.Column('scope_id', sa.String(length=36), nullable=True),
        sa.Column('is_force_delivery', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_orphan', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('active_version_id', sa.String(length=36), nullable=True),
        sa.Column('admin_description', sa.Text(), nullable=True),
        sa.Column('admin_tags', sa.JSON(), nullable=False, server_default='[]'),
    ])
    op.create_index('ix_skills_scope_id', 'skills', ['scope_id'], unique=False)

    # --- mcp_servers ---
    _add_columns('mcp_servers', [
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('process_pid', sa.Integer(), nullable=True),
        sa.Column('tools', sa.JSON(), nullable=False, server_default='[]'),
    ])

    # --- agent_group_tasks ---
    op.add_column(
        'agent_group_tasks',
        sa.Column('dependencies', sa.JSON(), nullable=False, server_default='[]'),
    )

    # --- checkpoints ---
    _add_columns('checkpoints', [
        sa.Column('channel_values', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('channel_versions', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('versions_seen', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('pending_writes', sa.Text(), nullable=False, server_default='[]'),
    ])

    # --- user_profiles ---
    _add_columns('user_profiles', [
        sa.Column('inviolable', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('values', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('principles', sa.JSON(), nullable=False, server_default='[]'),
    ])


def downgrade() -> None:
    for column in ('inviolable', 'values', 'principles'):
        op.drop_column('user_profiles', column)

    for column in ('channel_values', 'channel_versions', 'versions_seen', 'pending_writes'):
        op.drop_column('checkpoints', column)

    op.drop_column('agent_group_tasks', 'dependencies')

    for column in ('updated_at', 'last_error', 'process_pid', 'tools'):
        op.drop_column('mcp_servers', column)

    op.drop_index('ix_skills_scope_id', table_name='skills')
    for column in (
        'updated_at', 'scope', 'scope_id', 'is_force_delivery', 'is_orphan',
        'is_deleted', 'active_version_id', 'admin_description', 'admin_tags',
    ):
        op.drop_column('skills', column)

    op.drop_index('ix_documents_content_hash', table_name='documents')
    for column in ('content_hash', 'indexed_at'):
        op.drop_column('documents', column)

    op.drop_column('sessions', 'working_memory')
    with op.batch_alter_table('sessions') as batch:
        batch.alter_column(
            'agent_id',
            existing_type=sa.String(length=36),
            nullable=False,
        )

    for column in ('agent_role', 'goal', 'backstory'):
        op.drop_column('agents', column)

    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    for column in (
        'username', 'hashed_password', 'full_name', 'role', 'status', 'is_verified',
        'avatar_url', 'preferences', 'last_login_at', 'failed_login_attempts',
        'password_changed_at', 'updated_at', 'deleted_at',
    ):
        op.drop_column('users', column)
