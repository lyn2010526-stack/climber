"""Retained as a chain terminator for the auto-loop task ownership column.

The idempotent implementation of this change lives in f6a7b8c9d0e1, which
inspects the live schema before touching it. Keeping d4e5f6a7b8c9 in the
history avoids rewriting an already-released revision id, but its body is a
no-op so a fresh database only ever applies the guarded version.

Revision ID: d4e5f6a7b8c9
Revises: f6a7b8c9d0e1
"""

from collections.abc import Sequence

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op: f6a7b8c9d0e1 already added owner_id and its index."""


def downgrade() -> None:
    """No-op: the column and index are owned by f6a7b8c9d0e1."""
