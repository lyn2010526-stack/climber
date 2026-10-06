"""Align the migration-chain schema with the ORM (users FKs and drifted columns).

The initial migration (``dd8212a8f22a``) declared ``<table>.user_id`` with a
foreign key to ``users.id`` on twenty tables, but no matching ORM model
declares one: ``user_id`` is a free-form owner string defaulting to
``default-user``, while the ORM ``users`` primary key is an autoincrement
integer (see ``f6a7b8c9d0e1``). No row can satisfy the constraint, so on
FK-enforcing backends (PostgreSQL, and SQLite through the application
connection) the first insert into any of these tables fails with
``FOREIGN KEY constraint failed``. This extends the earlier ``user_settings``
fix (``a1b2c3d4e5f8``) to the remaining tables.

The same revision adds the columns the ORM grew after the chain was written, so
a database built purely by ``alembic upgrade head`` matches one built by
``Base.metadata.create_all``:

* ``agent_group_tasks.dependencies``
* ``auto_loop_tasks`` retry / interruption / checkpoint fields
* ``checkpoints`` Pregel channel snapshots
* ``mcp_servers`` tool cache and process bookkeeping

It also restores indexes the ORM declares but the chain never created (the
earlier batch rebuilds dropped them), so ``alembic upgrade head`` and
``Base.metadata.create_all`` agree on index coverage too.

Every step is guarded: ``create_all`` databases already carry the ORM shape and
are left untouched.

Revision ID: e7f8a9b0c1d2
Revises: f6a7b8c9d0e1
Create Date: 2026-10-06 11:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from migration_support import columns as _columns
from migration_support import existing_indexes as _indexes
from migration_support import has_table as _has_table

revision: str = "e7f8a9b0c1d2"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables whose ``user_id`` column carries a ``users.id`` FK the ORM does not.
USER_FK_TABLES: tuple[str, ...] = (
    "agent_groups",
    "api_keys",
    "archival_passages",
    "audit_logs",
    "budget_configs",
    "core_memory_blocks",
    "cost_records",
    "documents",
    "episodic_memories",
    "eval_datasets",
    "eval_runs",
    "feedback",
    "knowledge_graph",
    "memory_retrieval_logs",
    "reasoning_feedback",
    "reasoning_traces",
    "trace_spans",
    "usage_logs",
    "usage_quotas",
    "user_profiles",
)

# (table, column, type, nullable, server_default). ``server_default`` is
# required so NOT NULL additions succeed on tables that already hold rows; it
# mirrors the ORM Python-side default (``[]`` / ``{}`` render as SQL literals).
MISSING_COLUMNS: tuple[tuple[str, str, sa.types.TypeEngine, bool, object], ...] = (
    ("agent_group_tasks", "dependencies", sa.JSON(), False, "[]"),
    ("auto_loop_tasks", "retry_count", sa.Integer(), False, "0"),
    ("auto_loop_tasks", "interruption_reason", sa.String(length=40), True, None),
    ("auto_loop_tasks", "checkpoint", sa.JSON(), True, None),
    ("auto_loop_tasks", "progress_evaluation", sa.JSON(), True, None),
    ("checkpoints", "channel_values", sa.Text(), False, "{}"),
    ("checkpoints", "channel_versions", sa.Text(), False, "{}"),
    ("checkpoints", "versions_seen", sa.Text(), False, "{}"),
    ("checkpoints", "pending_writes", sa.Text(), False, "[]"),
    ("mcp_servers", "tools", sa.JSON(), False, "[]"),
    ("mcp_servers", "process_pid", sa.Integer(), True, None),
    ("mcp_servers", "last_error", sa.Text(), True, None),
    ("mcp_servers", "updated_at", sa.DateTime(), False, sa.text("CURRENT_TIMESTAMP")),
)

# (table, index name, columns, unique). The ORM declares these while the chain
# never created them, so a ``create_all`` database is indexed and an
# ``alembic upgrade head`` database is not. Names follow SQLAlchemy's default
# (``ix_<table>_<column>``) so both backends end up identical.
MISSING_INDEXES: tuple[tuple[str, str, tuple[str, ...], bool], ...] = (
    ("auth_api_keys", "ix_auth_api_keys_key_hash", ("key_hash",), True),
    ("auth_api_keys", "ix_auth_api_keys_owner", ("owner",), False),
    ("auto_loop_tasks", "ix_auto_loop_tasks_heartbeat_at", ("heartbeat_at",), False),
    ("auto_loop_tasks", "ix_auto_loop_tasks_owner_id", ("owner_id",), False),
    ("auto_loop_tasks", "ix_auto_loop_tasks_status", ("status",), False),
    ("cost_records", "ix_cost_records_group_id", ("group_id",), False),
    ("cost_records", "ix_cost_records_task_id", ("task_id",), False),
    ("lifecycle_memories", "ix_lifecycle_memories_agent_id", ("agent_id",), False),
    ("lifecycle_memories", "ix_lifecycle_memories_user_id", ("user_id",), False),
    ("session_personas", "ix_session_personas_base_persona_id", ("base_persona_id",), False),
    ("user_activities", "ix_user_activities_user_id", ("user_id",), False),
    ("user_instruction_traces", "ix_user_instruction_traces_status", ("status",), False),
    ("user_invitations", "ix_user_invitations_email", ("email",), False),
    ("user_preferences", "ix_user_preferences_user_id", ("user_id",), False),
    ("user_sessions", "ix_user_sessions_user_id", ("user_id",), False),
)

# The initial migration declared its FKs unnamed, so a reflected SQLite table
# exposes them without a name; this convention makes them addressable.
_FK_NAMING = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}


def _fk_name(table: str) -> str:
    return f"fk_{table}_user_id_users"


def _postgres_fk_name(table: str) -> str:
    """The name PostgreSQL gave the initial migration's unnamed FK.

    ``op.create_table`` only applies a naming convention that declares an
    ``fk`` key, and the metadata has none, so PostgreSQL auto-named every
    constraint ``<table>_<column>_fkey``. Only used in ``--sql`` mode, where
    there is no schema to inspect.
    """
    return f"{table}_user_id_fkey"


def _frozen(table: str, *, with_fk: bool) -> sa.Table:
    """ORM-shaped copy of ``table`` for the offline batch rebuild.

    ``--sql`` mode has no database to reflect, so batch mode needs a complete
    ``copy_from`` definition. Taking it from the ORM keeps the rendered table
    exact without hand-copying twenty column lists.

    Batch mode rebuilds the table but skips indexes that originate from a
    column's ``index=True`` / ``unique=True`` flag (it resets those flags on the
    copied columns), so they are re-declared here as explicit table-level
    indexes to survive the render.

    The ``users`` FK is appended explicitly because the ORM never declares it
    and batch mode needs it present in the pre-state in order to drop it.
    """
    import app.storage  # noqa: F401 - registers every model on Base.metadata
    from app.storage import Base

    frozen = Base.metadata.tables[table].to_metadata(sa.MetaData())
    for index in list(frozen.indexes):
        columns = [frozen.c[column.name] for column in index.columns]
        frozen.indexes.discard(index)
        sa.Index(index.name, *columns, unique=index.unique, _table=frozen)
    if with_fk:
        frozen.append_constraint(
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=_fk_name(table))
        )
    return frozen


def _offline() -> bool:
    try:
        return bool(op.get_context().as_sql)
    except Exception:
        return False


def _present(table: str) -> bool:
    """Whether the table exists. Offline every guarded step is emitted."""
    return _offline() or _has_table(table)


def _user_fk(table: str) -> tuple[bool, str | None]:
    """Report whether ``table.user_id`` references ``users.id`` and its name.

    Offline there is no schema to inspect, so the FK is reported present with no
    name and the caller falls back to the backend's default constraint name.
    """
    if _offline():
        return True, None
    if not _has_table(table):
        return False, None
    for fk in sa.inspect(op.get_bind()).get_foreign_keys(table):
        referred = fk.get("referred_table")
        constrained = list(fk.get("constrained_columns") or [])
        if referred == "users" and constrained == ["user_id"]:
            return True, fk.get("name")
    return False, None


def _batch(table: str, *, with_fk: bool):
    """Batch context for a rebuild that drops (or restores) the users FK.

    Online the table is reflected, so nothing but the FK changes. Offline there
    is nothing to reflect and the frozen ORM definition is used instead.
    """
    if _offline():
        return op.batch_alter_table(table, copy_from=_frozen(table, with_fk=with_fk))
    return op.batch_alter_table(table, naming_convention=_FK_NAMING)


def upgrade() -> None:
    dialect = op.get_context().dialect.name

    for table, column, type_, nullable, default in MISSING_COLUMNS:
        if not _present(table) or column in _columns(table):
            continue
        op.add_column(table, sa.Column(column, type_, nullable=nullable, server_default=default))

    for table in USER_FK_TABLES:
        if not _present(table):
            continue
        present, name = _user_fk(table)
        if not present:
            continue
        if dialect == "sqlite":
            # SQLite cannot drop constraints in place; rebuild the table, which
            # the ORM shape makes FK-free.
            with _batch(table, with_fk=True) as batch:
                batch.drop_constraint(_fk_name(table), type_="foreignkey")
        else:
            op.drop_constraint(name or _postgres_fk_name(table), table, type_="foreignkey")

    # After the batch rebuilds: their ``copy_from`` re-declares ORM indexes, so
    # anything created before them would be dropped again.
    for table, index_name, columns, unique in MISSING_INDEXES:
        if not _present(table) or index_name in _indexes(table):
            continue
        op.create_index(index_name, table, list(columns), unique=unique)


def downgrade() -> None:
    dialect = op.get_context().dialect.name

    for table in reversed(USER_FK_TABLES):
        if not _present(table):
            continue
        present, _name = _user_fk(table)
        if present:
            continue
        if dialect == "sqlite":
            with _batch(table, with_fk=False) as batch:
                batch.create_foreign_key(_fk_name(table), "users", ["user_id"], ["id"])
        else:
            op.create_foreign_key(_fk_name(table), table, "users", ["user_id"], ["id"])

    for table, column, _type, _nullable, _default in reversed(MISSING_COLUMNS):
        if _present(table) and column in _columns(table):
            op.drop_column(table, column)

    # Last: the batch rebuilds above re-declare ORM indexes, so their copies are
    # removed here too rather than in a separate earlier pass.
    for table, index_name, _index_columns, _unique in reversed(MISSING_INDEXES):
        if not _present(table) or index_name not in _indexes(table):
            continue
        op.drop_index(index_name, table_name=table)
