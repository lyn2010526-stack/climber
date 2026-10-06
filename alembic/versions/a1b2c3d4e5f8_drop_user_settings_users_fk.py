"""Drop the user_settings -> users foreign key to match the ORM.

The ``b2c3d4e5f6a7`` migration created ``user_settings.user_id`` with a
foreign key to ``users.id``, but the ``UserSettings`` model declares no such
foreign key and the default/local principal (``default-user``) never has a
``users`` row. On FK-enforcing backends (e.g. PostgreSQL) the first settings
write therefore fails. R9-16.

The table is rebuilt from a frozen definition that matches the current ORM so
the removal works on SQLite (which cannot drop constraints) and on backends
that only support unnamed constraints after reflection.

Revision ID: a1b2c3d4e5f8
Revises: a1b2c3d4e5f7
Create Date: 2026-10-04 00:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f8"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "user_settings"
CONSTRAINT_NAME = "fk_user_settings_user_id_users"


def _table(*, with_fk: bool) -> sa.Table:
    """Frozen user_settings definition; mirrors the ORM exactly."""
    metadata = sa.MetaData()
    return sa.Table(
        TABLE,
        metadata,
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("autonomous_agent_mode", sa.Boolean(), nullable=True),
        sa.Column("token_throttle_mcp_enabled", sa.Boolean(), nullable=True),
        sa.Column("mcp_status", sa.String(length=20), nullable=True),
        sa.Column("notifications", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)")),
        *(
            (sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=CONSTRAINT_NAME),)
            if with_fk
            else ()
        ),
    )


def _has_fk() -> bool:
    if op.get_context().as_sql:
        # Offline has no schema to inspect; the revision's premise is that the
        # FK exists, so emit the rebuild.
        return True
    inspector = sa.inspect(op.get_bind())
    if TABLE not in inspector.get_table_names():
        return False
    return any(
        fk.get("referred_table") == "users" and fk.get("constrained_columns") == ["user_id"]
        for fk in inspector.get_foreign_keys(TABLE)
    )


def upgrade() -> None:
    if not _has_fk():
        return
    with op.batch_alter_table(TABLE, copy_from=_table(with_fk=True)) as batch:
        batch.drop_constraint(CONSTRAINT_NAME, type_="foreignkey")


def downgrade() -> None:
    if _has_fk():
        return
    with op.batch_alter_table(TABLE, copy_from=_table(with_fk=False)) as batch:
        batch.create_foreign_key(CONSTRAINT_NAME, "users", ["user_id"], ["id"])
