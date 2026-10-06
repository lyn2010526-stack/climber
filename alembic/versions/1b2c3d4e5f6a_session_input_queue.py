"""Persist the session steering and follow-up queues."""

import sqlalchemy as sa
from alembic import op
from migration_support import has_table

revision = "1b2c3d4e5f6a"
down_revision = "0a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade():
    if has_table("session_inputs"):
        return
    op.create_table(
        "session_inputs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("client_request_id", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.UniqueConstraint("session_id", "client_request_id", name="uq_session_input_request"),
        sa.UniqueConstraint("session_id", "sequence", name="uq_session_input_sequence"),
    )
    op.create_index("ix_session_inputs_session_id", "session_inputs", ["session_id"])


def downgrade():
    op.drop_table("session_inputs")
