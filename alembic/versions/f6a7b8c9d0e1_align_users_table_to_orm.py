"""Rebuild the migration-chain ``users`` table to match the ORM model.

The initial migration (dd8212a8f22a) created ``users`` with a ``String(36)``
uuid primary key and the legacy ``email`` / ``password_hash`` / ``is_active``
/ ``is_admin`` column set, while the ORM (``app.models.users.User``) declares
an ``Integer`` autoincrement primary key and the full profile column set
(``username``, ``hashed_password``, ``role``, ``status``, ...).

Live databases are built by ``Base.metadata.create_all`` (see
``app.storage.init_db``), so they already carry the ORM shape. Only a database
created purely by ``alembic upgrade head`` ever saw the legacy shape — and
every ORM insert against it failed on the missing NOT NULL ``username`` /
``hashed_password`` columns, so no usable rows exist there.

This revision rebuilds the table to the exact ORM shape using
``batch_alter_table`` (required on SQLite, where column-type changes go
through a table rebuild): adds the missing profile columns (NOT NULL ones
with a migration-time server default, mirroring the ORM Python-side
defaults), converts ``id`` from ``VARCHAR(36)`` to ``INTEGER``, drops the
legacy columns, and recreates the two unique indexes. Legacy-shaped rows
carry over best effort; a ``String`` id that is not numeric keeps its text
value under SQLite affinity rules.

Databases already carrying the ORM shape are detected via the ``username``
column and left untouched.

Revision ID: f6a7b8c9d0e1
Revises: f5a6b7c8d9e0
Create Date: 2026-10-06 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "f5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_COLUMNS = ("password_hash", "is_active", "is_admin")


def _offline() -> bool:
    return bool(op.get_context().as_sql)


def _legacy_users_table() -> sa.Table:
    """Frozen pre-revision definition; only used to render ``--sql`` batches."""
    metadata = sa.MetaData()
    return sa.Table(
        "users",
        metadata,
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def _batch():
    """Batch context reflecting the live table online, frozen table offline."""
    if _offline():
        return op.batch_alter_table("users", copy_from=_legacy_users_table())
    return op.batch_alter_table("users")


def _orm_profile_columns() -> list[sa.Column]:
    """ORM columns missing from the legacy table.

    Inline (not reflected from ``app.models.users``) so offline ``--sql``
    rendering has no ORM import dependency. NOT NULL columns get a
    migration-time ``server_default`` mirroring the ORM Python-side default;
    without it the batch data copy would fail on legacy rows.
    """
    return [
        sa.Column("username", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("hashed_password", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("full_name", sa.String(length=128), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="viewer"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("is_verified", sa.Boolean(), nullable=True),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("preferences", sa.Text(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    ]


def upgrade() -> None:
    from migration_support import columns as _columns
    from migration_support import existing_indexes as _indexes

    existing = _columns("users")
    if existing and "username" in existing:
        # ORM-shaped table (typical create_all database): nothing to do.
        return
    with _batch() as batch:
        for column in _orm_profile_columns():
            if column.name not in existing:
                batch.add_column(column)
        # R11-H18: ORM primary key is Integer/autoincrement, not String(36).
        batch.alter_column(
            "id",
            existing_type=sa.String(length=36),
            type_=sa.Integer(),
            existing_nullable=False,
        )
        # ORM declares VARCHAR(256); the initial migration used 255.
        batch.alter_column(
            "email",
            existing_type=sa.String(length=255),
            type_=sa.String(length=256),
            existing_nullable=False,
        )
        for legacy in _LEGACY_COLUMNS:
            if legacy in existing:
                batch.drop_column(legacy)
    if "ix_users_username" not in _indexes("users"):
        op.create_index("ix_users_username", "users", ["username"], unique=True)
    if "ix_users_email" not in _indexes("users"):
        op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    from migration_support import columns as _columns
    from migration_support import existing_indexes as _indexes

    existing = _columns("users")
    if not existing or "password_hash" in existing:
        # Legacy-shaped (or absent) table: nothing to roll back.
        return
    # Drop the ORM unique indexes before the rebuild: batch mode carries
    # reflected indexes over to the new table, and ix_users_username would
    # reference the about-to-be-dropped username column.
    if "ix_users_username" in _indexes("users"):
        op.drop_index("ix_users_username", table_name="users")
    if "ix_users_email" in _indexes("users"):
        op.drop_index("ix_users_email", table_name="users")
    with _batch() as batch:
        batch.alter_column(
            "id",
            existing_type=sa.Integer(),
            type_=sa.String(length=36),
            existing_nullable=False,
        )
        batch.add_column(sa.Column("password_hash", sa.String(length=255), nullable=False, server_default=""))
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.alter_column(
            "email",
            existing_type=sa.String(length=256),
            type_=sa.String(length=255),
            existing_nullable=False,
        )
        for column in _orm_profile_columns():
            if column.name in existing:
                batch.drop_column(column.name)
