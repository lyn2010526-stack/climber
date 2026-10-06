"""Persist owner-scoped notification configuration."""

from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def _offline() -> bool:
    return bool(op.get_context().as_sql)


def _user_settings_table(*, include_legacy: bool) -> sa.Table:
    """Frozen definition used only when ``--sql`` mode has no DB to reflect.

    ``include_legacy`` mirrors the live schema each batch runs against: the
    legacy ``enhanced_prompt_enabled`` column only exists on databases built by
    the migration chain before this revision's upgrade rebuilds the table.
    """
    metadata = sa.MetaData()
    columns = [
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("autonomous_agent_mode", sa.Boolean(), nullable=False),
        sa.Column("token_throttle_mcp_enabled", sa.Boolean(), nullable=False),
        sa.Column("mcp_status", sa.String(length=20), nullable=False),
        sa.Column("notifications", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]
    if include_legacy:
        columns.insert(5, sa.Column("enhanced_prompt_enabled", sa.Boolean(), nullable=True))
    return sa.Table("user_settings", metadata, *columns)


def _batch(*, include_legacy: bool):
    """Batch context that reflects the live table online, and uses the frozen
    definition offline. Passing ``copy_from`` online makes Alembic copy from a
    stale column list and can reference columns that are not on the real table.
    """
    if _offline():
        return op.batch_alter_table(
            "user_settings", copy_from=_user_settings_table(include_legacy=include_legacy)
        )
    return op.batch_alter_table("user_settings")


def upgrade() -> None:
    from migration_support import columns

    info = _column_defaults()
    existing = columns("user_settings")
    if "notifications" not in existing:
        op.add_column("user_settings", sa.Column("notifications", sa.JSON(), nullable=False, server_default="{}"))
    # Older migrations kept a required column that the current ORM no longer writes.
    if "enhanced_prompt_enabled" in existing and info.get("enhanced_prompt_enabled") in (None, ""):
        with _batch(include_legacy=True) as batch:
            batch.alter_column("enhanced_prompt_enabled", existing_type=sa.Boolean(), server_default=sa.false())


def _column_defaults() -> dict[str, object]:
    if _offline():
        # Offline cannot introspect; assume the legacy column has no default.
        return {"enhanced_prompt_enabled": None}
    return {
        column["name"]: column["default"]
        for column in sa.inspect(op.get_bind()).get_columns("user_settings")
    }


def downgrade() -> None:
    from migration_support import columns

    existing = columns("user_settings")
    # Batch rendering must mirror the live table exactly: the legacy column is
    # only present on databases that reached this revision through the original
    # chain. A create_all-shaped database never had it.
    include_legacy = "enhanced_prompt_enabled" in existing
    # Only drop what upgrade created; never drop a pre-existing column.
    if "notifications" in existing:
        with _batch(include_legacy=include_legacy) as batch:
            batch.drop_column("notifications")
    # Restore the pre-upgrade state: enhanced_prompt_enabled had no server_default.
    if include_legacy:
        with _batch(include_legacy=True) as batch:
            batch.alter_column("enhanced_prompt_enabled", existing_type=sa.Boolean(), server_default=None)
