"""
create user instruction traces

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-09-30 16:55:03.707733
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "user_instruction_traces"


def upgrade() -> None:
    if TABLE in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        TABLE,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("intent_summary", sa.Text(), nullable=True),
        sa.Column("task_spec", sa.JSON(), nullable=True),
        sa.Column("goal_preserved", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("compressed_into_id", sa.String(length=36), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source IN ('chat', 'api', 'cli')",
            name="ck_user_instruction_traces_source",
        ),
        sa.CheckConstraint(
            "compressed_into_id IS NULL OR compressed_into_id <> id",
            name="ck_user_instruction_traces_compression_self",
        ),
        sa.CheckConstraint(
            "token_count >= 0",
            name="ck_user_instruction_traces_token_count",
        ),
        sa.ForeignKeyConstraint(["compressed_into_id"], [f"{TABLE}.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_instruction_traces_session_id"), TABLE, ["session_id"], unique=False
    )
    op.create_index(
        op.f("ix_user_instruction_traces_user_id"), TABLE, ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_user_instruction_traces_text_hash"), TABLE, ["text_hash"], unique=False
    )
    op.create_index(
        op.f("ix_user_instruction_traces_source"), TABLE, ["source"], unique=False
    )
    op.create_index(
        op.f("ix_user_instruction_traces_is_archived"), TABLE, ["is_archived"], unique=False
    )
    op.create_index(
        op.f("ix_user_instruction_traces_compressed_into_id"),
        TABLE,
        ["compressed_into_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_instruction_traces_session_created", TABLE, ["session_id", "created_at"]
    )
    op.create_index(
        "ix_user_instruction_traces_user_created", TABLE, ["user_id", "created_at"]
    )
    op.create_index(
        "ix_user_instruction_traces_hash_created", TABLE, ["text_hash", "created_at"]
    )


def downgrade() -> None:
    if TABLE not in sa.inspect(op.get_bind()).get_table_names():
        return
    op.drop_index("ix_user_instruction_traces_hash_created", table_name=TABLE)
    op.drop_index("ix_user_instruction_traces_user_created", table_name=TABLE)
    op.drop_index("ix_user_instruction_traces_session_created", table_name=TABLE)
    op.drop_index(op.f("ix_user_instruction_traces_compressed_into_id"), table_name=TABLE)
    op.drop_index(op.f("ix_user_instruction_traces_is_archived"), table_name=TABLE)
    op.drop_index(op.f("ix_user_instruction_traces_source"), table_name=TABLE)
    op.drop_index(op.f("ix_user_instruction_traces_text_hash"), table_name=TABLE)
    op.drop_index(op.f("ix_user_instruction_traces_user_id"), table_name=TABLE)
    op.drop_index(op.f("ix_user_instruction_traces_session_id"), table_name=TABLE)
    op.drop_table(TABLE)
