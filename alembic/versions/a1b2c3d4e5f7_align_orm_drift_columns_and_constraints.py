"""Align ORM columns and constraints missing from the migration chain.

Covers the database/storage drift reported as R13-17, R13-18, R13-19, R13-20,
R13-21, R13-22, R13-12 and R13-09:

* sessions.working_memory (JSON)
* sessions.agent_id nullable (ORM is nullable, initial migration was NOT NULL)
* documents.content_hash / documents.indexed_at
* agents.agent_role / goal / backstory and agents.system_prompt nullable
* skills scope fields (scope, scope_id, is_force_delivery, is_orphan,
  is_deleted, active_version_id, admin_description, admin_tags, updated_at)
* user_profiles.inviolable / values / principles
* agent_group_members unique (group_id, agent_id)
* core_memory_blocks unique (user_id, agent_id, label)
* cost_records.group_id / task_id (group cost attribution, R12-H54)

Every step is guarded so databases built by ``create_all`` (which already carry
the ORM shape) are left untouched.

Revision ID: a1b2c3d4e5f7
Revises: f0a1b2c3d4e5
Create Date: 2026-10-03 23:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from migration_support import columns as _columns
from migration_support import has_table as _has_table
from migration_support import existing_indexes as _indexes
from migration_support import existing_unique as _existing_unique

revision: str = "a1b2c3d4e5f7"
down_revision: str | Sequence[str] | None = "f0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_missing(table: str, columns: list[sa.Column]) -> None:
    existing = _columns(table)
    for column in columns:
        if column.name not in existing:
            op.add_column(table, column)


def _has_index(table: str, name: str) -> bool:
    return name in _indexes(table)


def _orm_table(name: str) -> sa.Table:
    """Return the live ORM table for offline batch rendering.

    The rebuilt table then matches the ORM shape exactly, which is the intent of
    this alignment revision. Falls back to a bare table name when the ORM is not
    importable (e.g. a trimmed migration-only environment).
    """
    try:
        import app.storage  # noqa: F401
        from app.storage import Base

        if name in Base.metadata.tables:
            return Base.metadata.tables[name]
    except Exception:
        pass
    return sa.Table(name, sa.MetaData())


def upgrade() -> None:
    # R13-17 / R13-18: sessions drift.
    _add_missing(
        "sessions",
        [
            sa.Column("working_memory", sa.JSON(), nullable=False, server_default="{}"),
        ],
    )
    if "agent_id" in _columns("sessions"):
        # R13-18: ORM declares agent_id nullable; the initial migration made it
        # NOT NULL, which blocks agent-less sessions.
        with op.batch_alter_table(
            "sessions", copy_from=_orm_table("sessions")
        ) as batch:
            batch.alter_column(
                "agent_id",
                existing_type=sa.String(length=36),
                existing_nullable=False,
                nullable=True,
            )

    # R13-19: documents hashing / indexing metadata.
    _add_missing(
        "documents",
        [
            sa.Column("content_hash", sa.String(length=64), nullable=True),
            sa.Column("indexed_at", sa.DateTime(), nullable=True),
        ],
    )
    if "content_hash" in _columns("documents"):
        if not _has_index("documents", "ix_documents_content_hash"):
            op.create_index("ix_documents_content_hash", "documents", ["content_hash"], unique=False)

    # R13-20: CrewAI-style agent role identity + system_prompt nullability.
    _add_missing(
        "agents",
        [
            sa.Column("agent_role", sa.String(length=255), nullable=True),
            sa.Column("goal", sa.Text(), nullable=True),
            sa.Column("backstory", sa.Text(), nullable=True),
        ],
    )
    if "system_prompt" in _columns("agents"):
        with op.batch_alter_table(
            "agents", copy_from=_orm_table("agents")
        ) as batch:
            batch.alter_column(
                "system_prompt",
                existing_type=sa.Text(),
                existing_nullable=False,
                nullable=True,
            )

    # R13-21: skills three-tier scope and lifecycle metadata.
    _add_missing(
        "skills",
        [
            sa.Column("scope", sa.String(length=20), nullable=False, server_default="global"),
            sa.Column("scope_id", sa.String(length=36), nullable=True),
            sa.Column("is_force_delivery", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_orphan", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("active_version_id", sa.String(length=36), nullable=True),
            sa.Column("admin_description", sa.Text(), nullable=True),
            sa.Column("admin_tags", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
            ),
        ],
    )
    existing_skill_indexes = _has_index("skills", "ix_skills_scope_id")
    if not existing_skill_indexes:
        op.create_index("ix_skills_scope_id", "skills", ["scope_id"], unique=False)

    # R13-22: user profile identity memory.
    _add_missing(
        "user_profiles",
        [
            sa.Column("inviolable", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("values", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("principles", sa.JSON(), nullable=False, server_default="[]"),
        ],
    )

    # R13-12: agent_group_members unique (group_id, agent_id).
    # SQLite allows NULL agent_id duplicates, matching the ORM's nullable column.
    _dedupe(
        "agent_group_members",
        ["group_id", "agent_id"],
        "id",
    )
    existing_member_constraints = _existing_unique("agent_group_members")
    if ("agent_id", "group_id") not in existing_member_constraints:
        if _has_index("agent_group_members", "uq_agent_group_member"):
            pass
        else:
            op.create_index(
                "uq_agent_group_member",
                "agent_group_members",
                ["group_id", "agent_id"],
                unique=True,
            )

    # R13-09: core_memory_blocks unique (user_id, agent_id, label).
    _dedupe(
        "core_memory_blocks",
        ["user_id", "agent_id", "label"],
        "id",
    )
    existing_block_constraints = _existing_unique("core_memory_blocks")
    if ("agent_id", "label", "user_id") not in existing_block_constraints:
        if _has_index("core_memory_blocks", "uq_core_memory_block_scope"):
            pass
        else:
            op.create_index(
                "uq_core_memory_block_scope",
                "core_memory_blocks",
                ["user_id", "agent_id", "label"],
                unique=True,
            )

    # R12-H54: group cost attribution.
    _add_missing(
        "cost_records",
        [
            sa.Column("group_id", sa.String(length=36), nullable=True),
            sa.Column("task_id", sa.String(length=36), nullable=True),
        ],
    )


def _dedupe(table: str, key_columns: list[str], id_column: str) -> None:
    """Keep the oldest row per key so a unique constraint can be added."""
    if not _has_table(table):
        return
    columns = _columns(table)
    if not set(key_columns).issubset(columns) or id_column not in columns:
        return
    key_sql = ", ".join(f'"{column}"' for column in key_columns)
    op.execute(
        sa.text(
            f'DELETE FROM "{table}" WHERE "{id_column}" NOT IN '
            f'(SELECT MIN("{id_column}") FROM "{table}" GROUP BY {key_sql})'
        )
    )


def downgrade() -> None:
    if _has_table("core_memory_blocks") and _has_index(
        "core_memory_blocks", "uq_core_memory_block_scope"
    ):
        op.drop_index("uq_core_memory_block_scope", table_name="core_memory_blocks")
    if _has_table("agent_group_members") and _has_index(
        "agent_group_members", "uq_agent_group_member"
    ):
        op.drop_index("uq_agent_group_member", table_name="agent_group_members")
    for column in ("inviolable", "values", "principles"):
        if column in _columns("user_profiles"):
            op.drop_column("user_profiles", column)
    if _has_index("skills", "ix_skills_scope_id"):
        op.drop_index("ix_skills_scope_id", table_name="skills")
    for column in (
        "scope",
        "scope_id",
        "is_force_delivery",
        "is_orphan",
        "is_deleted",
        "active_version_id",
        "admin_description",
        "admin_tags",
        "updated_at",
    ):
        if column in _columns("skills"):
            op.drop_column("skills", column)
    for column in ("agent_role", "goal", "backstory"):
        if column in _columns("agents"):
            op.drop_column("agents", column)
    if _has_index("documents", "ix_documents_content_hash"):
        op.drop_index("ix_documents_content_hash", table_name="documents")
    for column in ("content_hash", "indexed_at"):
        if column in _columns("documents"):
            op.drop_column("documents", column)
    if "working_memory" in _columns("sessions"):
        op.drop_column("sessions", "working_memory")
    for column in ("group_id", "task_id"):
        if column in _columns("cost_records"):
            op.drop_column("cost_records", column)
