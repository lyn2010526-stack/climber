"""add auth and profile tables missing from the migration chain

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-30 17:40:00.000000

Eight ORM tables (auth keys, user sessions/activities/preferences/invitations,
personas and lifecycle memories) were only ever created by
`Base.metadata.create_all`; no revision produced them. Without this, a database
built purely from migrations is missing the tables the user-profile subsystem
depends on. Every statement is guarded so create_all-built databases are
untouched, and the definitions are frozen here rather than read from the ORM.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b8c9d0e1f2a3'
down_revision: str | None = 'a7b8c9d0e1f2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    'auth_api_keys',
    'lifecycle_memories',
    'personas',
    'session_personas',
    'user_activities',
    'user_invitations',
    'user_preferences',
    'user_sessions',
)


def _has_table(name: str) -> bool:
    from migration_support import has_table

    return has_table(name)


def upgrade() -> None:
    if not _has_table('auth_api_keys'):
        op.create_table(
            'auth_api_keys',
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
            sa.PrimaryKeyConstraint('id'),
        )

    if not _has_table('lifecycle_memories'):
        op.create_table(
            'lifecycle_memories',
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
            sa.PrimaryKeyConstraint('id'),
        )

    if not _has_table('personas'):
        op.create_table(
            'personas',
            sa.Column('agent_id', sa.String(length=36), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('role', sa.String(length=255), nullable=False),
            sa.Column('personality_traits', sa.JSON(), nullable=False),
            sa.Column('expertise', sa.JSON(), nullable=False),
            sa.Column('communication_style', sa.String(length=500), nullable=False),
            sa.Column('goals', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.String(length=50), nullable=False),
            sa.Column('updated_at', sa.String(length=50), nullable=False),
            sa.PrimaryKeyConstraint('agent_id'),
        )

    if not _has_table('session_personas'):
        op.create_table(
            'session_personas',
            sa.Column('session_id', sa.String(length=36), nullable=False),
            sa.Column('base_persona_id', sa.String(length=36), nullable=False),
            sa.Column('overrides', sa.JSON(), nullable=False),
            sa.Column('learnings', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.String(length=50), nullable=False),
            sa.PrimaryKeyConstraint('session_id'),
        )

    if not _has_table('user_activities'):
        op.create_table(
            'user_activities',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('action', sa.String(length=64), nullable=False),
            sa.Column('resource_type', sa.String(length=64), nullable=True),
            sa.Column('resource_id', sa.String(length=128), nullable=True),
            sa.Column('ip_address', sa.String(length=64), nullable=True),
            sa.Column('user_agent', sa.String(length=512), nullable=True),
            sa.Column('metadata_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )

    if not _has_table('user_invitations'):
        op.create_table(
            'user_invitations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(length=256), nullable=False),
            sa.Column('token_hash', sa.String(length=128), nullable=False),
            sa.Column('invited_by', sa.Integer(), nullable=False),
            sa.Column('role', sa.String(length=32), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('accepted_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('token_hash'),
        )

    if not _has_table('user_preferences'):
        op.create_table(
            'user_preferences',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('key', sa.String(length=128), nullable=False),
            sa.Column('value', sa.Text(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )

    if not _has_table('user_sessions'):
        op.create_table(
            'user_sessions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('token_hash', sa.String(length=128), nullable=False),
            sa.Column('refresh_token_hash', sa.String(length=128), nullable=True),
            sa.Column('ip_address', sa.String(length=64), nullable=True),
            sa.Column('user_agent', sa.String(length=512), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('token_hash'),
            sa.UniqueConstraint('refresh_token_hash'),
        )


def downgrade() -> None:
    for name in reversed(TABLES):
        if _has_table(name):
            op.drop_table(name)
