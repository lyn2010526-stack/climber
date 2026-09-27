"""no-op placeholder for a superseded schema revision

Revision ID: 52310c24d4c8
Revises: dd8212a8f22a
Create Date: 2026-07-28 06:50:37.331201

This revision was originally generated with a full duplicate of the initial
schema and added an ``enhanced_prompt_enabled`` column to ``user_settings``.

Facts verified on 2026-09-26:

- The full schema is already created by the initial revision ``dd8212a8f22a``,
  so replaying a second copy of every ``create_table`` fails on any database
  that already has those tables.
- ``enhanced_prompt_enabled`` has no reader anywhere in the codebase, is absent
  from ``app/storage/models_platform.py``, and is absent from the live
  ``user_settings`` table. The column was never a supported feature.

The revision is kept in the chain because databases already stamped with
``52310c24d4c8`` must still resolve their history. It intentionally performs no
schema operation. The unreachable duplicate body has been removed so the file
states exactly what it does.
"""

from collections.abc import Sequence

revision: str = "52310c24d4c8"
down_revision: str | None = "dd8212a8f22a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No schema change: see the module docstring."""


def downgrade() -> None:
    """No schema change: see the module docstring."""
