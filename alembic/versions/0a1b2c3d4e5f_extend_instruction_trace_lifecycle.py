"""extend instruction traces with task lifecycle fields

Revision ID: 0a1b2c3d4e5f
Revises: f1a2b3c4d5e6
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from migration_support import existing_indexes as _existing_indexes
from migration_support import columns as _columns

revision: str = "0a1b2c3d4e5f"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = _columns("user_instruction_traces")
    additions = (
        ("turn_id", sa.String(length=36)),
        ("status", sa.String(length=20), {"server_default": "received"}),
        ("outcome", sa.String(length=20)),
        ("retrieval_count", sa.Integer(), {"server_default": "0"}),
        ("last_retrieved_at", sa.DateTime()),
        ("decayed_at", sa.DateTime()),
        ("completed_at", sa.DateTime()),
    )
    for item in additions:
        name, column, *kwargs = item
        if name not in columns:
            op.add_column("user_instruction_traces", sa.Column(name, column, nullable=True, **(kwargs[0] if kwargs else {})))
    if "ix_user_instruction_traces_turn_id" not in _existing_indexes("user_instruction_traces"):
        op.create_index("ix_user_instruction_traces_turn_id", "user_instruction_traces", ["turn_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_instruction_traces_turn_id", table_name="user_instruction_traces")
    for name in ("completed_at", "decayed_at", "last_retrieved_at", "retrieval_count", "outcome", "status", "turn_id"):
        op.drop_column("user_instruction_traces", name)
