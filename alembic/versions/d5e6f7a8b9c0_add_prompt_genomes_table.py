"""
add prompt genomes table

Revision ID: d5e6f7a8b9c0
Revises: c9d0e1f2a3b4
Create Date: 2026-10-01 10:00:00.000000

One table behind the genetic evolution loop: prompt_genomes stores evolved
prompt/parameter candidates per user, upserted by (user_id, genome_id). The
table is guarded so create_all-built databases are untouched, and the
definition is frozen here rather than read from the ORM.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GENOMES = "prompt_genomes"


def _has_table(name: str) -> bool:
    from migration_support import has_table

    return has_table(name)


def upgrade() -> None:
    if _has_table(GENOMES):
        return
    op.create_table(
        GENOMES,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("genome_id", sa.String(length=256), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("model_params", sa.JSON(), nullable=False),
        sa.Column("scores", sa.JSON(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("parent_ids", sa.JSON(), nullable=False),
        sa.Column("composite_score", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "genome_id", name="uq_prompt_genomes_user_genome"),
    )
    op.create_index(op.f("ix_prompt_genomes_user_id"), GENOMES, ["user_id"], unique=False)
    op.create_index(
        op.f("ix_prompt_genomes_composite_score"),
        GENOMES,
        ["composite_score"],
        unique=False,
    )


def downgrade() -> None:
    if not _has_table(GENOMES):
        return
    op.drop_index(op.f("ix_prompt_genomes_composite_score"), table_name=GENOMES)
    op.drop_index(op.f("ix_prompt_genomes_user_id"), table_name=GENOMES)
    op.drop_table(GENOMES)
