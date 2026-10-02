"""Placeholder revision for the duplicated-initial-schema incident.

The autogenerate run that produced this revision pasted a second copy of the
whole initial schema into upgrade()/downgrade(), behind an early ``return``:
roughly 800 lines of unreachable code that also disagreed with dd8212a8f22a
(extra columns on mcp_servers, skills, ...). Running it would have crashed the
chain, so it was kept as a no-op; the dead code is now removed outright.

What the filename promises (user_settings.enhanced_prompt_enabled) is created
by b2c3d4e5f6a7, and auto_loop_tasks -- the one table initial never created --
is handled by d4e5f6a7b8c9.

Revision ID: 52310c24d4c8
Revises: dd8212a8f22a
Create Date: 2026-07-28 06:50:37.331201
"""

from collections.abc import Sequence

revision: str = "52310c24d4c8"
down_revision: str | None = "dd8212a8f22a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Intentional no-op. Must stay so databases that already recorded this
    # revision keep a valid chain position.
    pass


def downgrade() -> None:
    pass
