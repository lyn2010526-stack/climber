"""Persist owner-scoped notification configuration."""

from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"]: column for column in sa.inspect(op.get_bind()).get_columns("user_settings")}
    if "notifications" not in columns:
        op.add_column("user_settings", sa.Column("notifications", sa.JSON(), nullable=False, server_default="{}"))
    # Older migrations kept a required column that the current ORM no longer writes.
    if "enhanced_prompt_enabled" in columns and columns["enhanced_prompt_enabled"]["default"] is None:
        with op.batch_alter_table("user_settings") as batch:
            batch.alter_column("enhanced_prompt_enabled", existing_type=sa.Boolean(), server_default=sa.false())


def downgrade() -> None:
    with op.batch_alter_table("user_settings") as batch:
        batch.drop_column("notifications")
