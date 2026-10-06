"""
merge session input queue and prompt genomes heads

Revision ID: f0a1b2c3d4e5
Revises: 1b2c3d4e5f6a, d5e6f7a8b9c0
Create Date: 2026-10-03 00:00:00.000000

Two independent feature branches landed without a shared descendant: the
session steering/follow-up queue (1b2c3d4e5f6a) and the prompt genomes table
(d5e6f7a8b9c0). This is a no-op merge revision that unifies the heads so that
`alembic upgrade head` resolves to a single tip again.
"""

from collections.abc import Sequence

revision: str = "f0a1b2c3d4e5"
down_revision: str | Sequence[str] | None = ("1b2c3d4e5f6a", "d5e6f7a8b9c0")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
