"""Persist in-flight agent run progress for crash recovery."""

import sqlalchemy as sa
from alembic import op
from migration_support import has_table

revision = "c1d2e3f4a5b6"
down_revision = "a1b2c3d4e5f8"
branch_labels = None
depends_on = None


def upgrade():
    if has_table("run_progress_snapshots"):
        return
    op.create_table(
        "run_progress_snapshots",
        sa.Column("session_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("turn_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("outer_round", sa.Integer(), nullable=False),
        sa.Column("current_subtask", sa.Text(), nullable=False),
        sa.Column("completed_subtasks_json", sa.Text(), nullable=False),
        sa.Column("followup_queue_json", sa.Text(), nullable=False),
        sa.Column("steering_queue_json", sa.Text(), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_run_progress_snapshots_status", "run_progress_snapshots", ["status"])
    op.create_index("ix_run_progress_snapshots_user_id", "run_progress_snapshots", ["user_id"])
    op.create_index("ix_run_progress_snapshots_heartbeat_at", "run_progress_snapshots", ["heartbeat_at"])


def downgrade():
    if not has_table("run_progress_snapshots"):
        return
    op.drop_index("ix_run_progress_snapshots_heartbeat_at", table_name="run_progress_snapshots")
    op.drop_index("ix_run_progress_snapshots_user_id", table_name="run_progress_snapshots")
    op.drop_index("ix_run_progress_snapshots_status", table_name="run_progress_snapshots")
    op.drop_table("run_progress_snapshots")
