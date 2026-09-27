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
    if any(column['name'] == 'model_settings' for column in sa.inspect(conn).get_columns('sessions')):
        return
    # Two separate batch passes, both required:
    #   pass 1  SQLite refuses ``ADD COLUMN ... NOT NULL`` without a default
    #           once ``sessions`` has rows, so backfill with ``'{}'`` first.
    #   pass 2  SQLite has no ``ALTER COLUMN ... DROP DEFAULT``; the DDL only
    #           reaches the right shape through a table recreate.  A single
    #           batch would instead create the column without its default and
    #           then fail the row copy.
    # The end state matches the ORM: ``model_settings JSON NOT NULL`` with no
    # server default (``Session.model_settings`` uses a Python-side ``default``).
    with op.batch_alter_table('sessions') as batch_op:
        batch_op.add_column(
            sa.Column('model_settings', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        )
    with op.batch_alter_table('sessions') as batch_op:
        batch_op.alter_column('model_settings', server_default=None)


def downgrade() -> None:
    conn = op.get_bind()
    if not any(column['name'] == 'model_settings' for column in sa.inspect(conn).get_columns('sessions')):
        return
    op.drop_column('sessions', 'model_settings')
