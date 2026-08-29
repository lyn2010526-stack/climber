"""add raw payload persistence records

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-08-28 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _inspector():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    if _inspector().has_table("raw_payloads"):
        return

    op.create_table(
        "raw_payloads",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("standard_fields", sa.JSON(), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("payload_ciphertext", sa.Text(), nullable=True),
        sa.Column("redaction_version", sa.String(length=10), nullable=False, server_default="1"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["turns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raw_payloads_run_id", "raw_payloads", ["run_id"], unique=False)
    op.create_index("ix_raw_payloads_message_id", "raw_payloads", ["message_id"], unique=False)


def downgrade() -> None:
    if not _inspector().has_table("raw_payloads"):
        return
    for name in ("ix_raw_payloads_message_id", "ix_raw_payloads_run_id"):
        if name in {index["name"] for index in _inspector().get_indexes("raw_payloads")}:
            op.drop_index(name, table_name="raw_payloads")
    op.drop_table("raw_payloads")
