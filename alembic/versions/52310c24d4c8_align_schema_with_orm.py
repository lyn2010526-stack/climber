"""align_schema_with_orm

Add the schema objects that dd8212a8f22a does not create, so that the
migration chain ends at the state the ORM in ``app/storage/`` actually
describes.

This revision was originally generated as a byte-for-byte copy of the
initial schema (48 ``op.create_table`` calls, 44 of which re-created
tables that dd8212a8f22a had already created).  Applying it raised
``DuplicateTable`` on a clean database, so it used to short-circuit with an
early ``return`` -- which silently dropped the objects unique to this
revision and left the database short 4 tables and 16 columns.

What genuinely belongs here, and only this:

* 4 new tables: ``archival_passages``, ``audit_logs``, ``auto_loop_tasks``,
  ``core_memory_blocks``
* 2 new indexes on existing tables: ``ix_documents_content_hash``,
  ``ix_skills_scope_id``
* 16 new columns on tables already created by dd8212a8f22a

The NOT NULL additions are backfilled in a first ``batch_alter_table`` pass
and have the temporary default stripped in a second pass, because SQLite
rejects ``ALTER TABLE ... ADD COLUMN ... NOT NULL`` without a default once
the target table has rows.  The end state therefore matches the ORM:
NOT NULL with no server default.

Revision ID: 52310c24d4c8
Revises: dd8212a8f22a
Create Date: 2026-07-28 06:50:37.331201
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '52310c24d4c8'
down_revision: str | None = 'dd8212a8f22a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Backfill values for the NOT NULL columns added below.  They mirror the
# Python-side defaults declared on the matching ORM attributes so existing
# rows are readable by the application immediately after the upgrade.
_BACKFILL_JSON_LIST = sa.text("'[]'")
_BACKFILL_FALSE = sa.text('0')
_BACKFILL_GLOBAL_SCOPE = sa.text("'global'")

# (table, column, type, nullable, backfill default, strip default afterwards).
# ``strip`` marks a backfill that exists only to make the ADD COLUMN legal on a
# populated SQLite table; the second pass removes it again so the end state
# matches the ORM (NOT NULL, no server default).
_ADDED_COLUMNS: tuple[tuple[str, str, object, bool, object | None, bool], ...] = (
    ('agent_group_tasks', 'dependencies', sa.JSON(), False, _BACKFILL_JSON_LIST, True),
    ('documents', 'content_hash', sa.String(length=64), True, None, False),
    ('documents', 'indexed_at', sa.DateTime(), True, None, False),
    ('mcp_servers', 'last_error', sa.Text(), True, None, False),
    ('mcp_servers', 'process_pid', sa.Integer(), True, None, False),
    ('mcp_servers', 'tools', sa.JSON(), False, _BACKFILL_JSON_LIST, True),
    ('mcp_servers', 'updated_at', sa.DateTime(), False, sa.text('(CURRENT_TIMESTAMP)'), False),
    ('skills', 'active_version_id', sa.String(length=36), True, None, False),
    ('skills', 'admin_description', sa.Text(), True, None, False),
    ('skills', 'admin_tags', sa.JSON(), False, _BACKFILL_JSON_LIST, True),
    ('skills', 'is_deleted', sa.Boolean(), False, _BACKFILL_FALSE, True),
    ('skills', 'is_force_delivery', sa.Boolean(), False, _BACKFILL_FALSE, True),
    ('skills', 'is_orphan', sa.Boolean(), False, _BACKFILL_FALSE, True),
    ('skills', 'scope', sa.String(length=20), False, _BACKFILL_GLOBAL_SCOPE, True),
    ('skills', 'scope_id', sa.String(length=36), True, None, False),
    ('skills', 'updated_at', sa.DateTime(), False, sa.text('(CURRENT_TIMESTAMP)'), False),
)


def _add_columns() -> None:
    """Add every column above, grouped into one recreate per table.

    Pass 1 attaches the real definition plus, where needed, a temporary
    server default.  Pass 2 strips those temporary defaults.  The two
    passes must stay separate: a single batch would create the new NOT NULL
    column without its default and then fail to copy pre-existing rows.
    """
    by_table: dict[str, list[tuple[str, str, object, bool, object | None, bool]]] = {}
    for entry in _ADDED_COLUMNS:
        by_table.setdefault(entry[0], []).append(entry)

    for table, columns in by_table.items():
        needs_strip = [column for _t, column, _ty, _n, _b, strip in columns if strip]
        with op.batch_alter_table(table) as batch_op:
            for _table, column, type_, nullable, backfill, _strip in columns:
                batch_op.add_column(
                    sa.Column(
                        column,
                        type_,
                        nullable=nullable,
                        server_default=backfill,
                    )
                )
        if needs_strip:
            with op.batch_alter_table(table) as batch_op:
                for column in needs_strip:
                    batch_op.alter_column(column, server_default=None)


def upgrade() -> None:
    op.create_table('auto_loop_tasks',
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
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_auto_loop_tasks_heartbeat_at'), 'auto_loop_tasks', ['heartbeat_at'], unique=False)
    op.create_index(op.f('ix_auto_loop_tasks_status'), 'auto_loop_tasks', ['status'], unique=False)
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
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
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
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_session_id'), 'audit_logs', ['session_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
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
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_core_memory_blocks_agent_id'), 'core_memory_blocks', ['agent_id'], unique=False)
    op.create_index(op.f('ix_core_memory_blocks_user_id'), 'core_memory_blocks', ['user_id'], unique=False)

    _add_columns()

    op.create_index(op.f('ix_documents_content_hash'), 'documents', ['content_hash'], unique=False)
    op.create_index(op.f('ix_skills_scope_id'), 'skills', ['scope_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_skills_scope_id'), table_name='skills')
    op.drop_index(op.f('ix_documents_content_hash'), table_name='documents')

    for table, column, _type, _nullable, _backfill, _strip in reversed(_ADDED_COLUMNS):
        op.drop_column(table, column)

    op.drop_index(op.f('ix_core_memory_blocks_user_id'), table_name='core_memory_blocks')
    op.drop_index(op.f('ix_core_memory_blocks_agent_id'), table_name='core_memory_blocks')
    op.drop_table('core_memory_blocks')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_session_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_archival_passages_user_id'), table_name='archival_passages')
    op.drop_index(op.f('ix_archival_passages_archive_id'), table_name='archival_passages')
    op.drop_table('archival_passages')
    op.drop_index(op.f('ix_auto_loop_tasks_status'), table_name='auto_loop_tasks')
    op.drop_index(op.f('ix_auto_loop_tasks_heartbeat_at'), table_name='auto_loop_tasks')
    op.drop_table('auto_loop_tasks')
