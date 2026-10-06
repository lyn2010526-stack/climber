"""Offline-safe schema inspection helpers for migrations.

``alembic upgrade --sql`` has no live database, so ``sa.inspect(op.get_bind())``
raises ``NoInspectionAvailable``. These helpers centralize the offline guard so
every revision behaves identically: in offline mode they report the table or
constraint as absent, which makes guarded DDL emit unconditionally into the
generated script.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


def _is_offline() -> bool:
    try:
        return bool(op.get_context().as_sql)
    except Exception:
        return False


def has_table(name: str) -> bool:
    if _is_offline():
        return False
    try:
        return name in sa.inspect(op.get_bind()).get_table_names()
    except sa.exc.NoInspectionAvailable:
        return False


def columns(table: str) -> set[str]:
    if _is_offline():
        return set()
    if not has_table(table):
        return set()
    try:
        return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}
    except sa.exc.NoInspectionAvailable:
        return set()


def existing_indexes(table: str) -> set[str]:
    if _is_offline():
        return set()
    try:
        return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}
    except sa.exc.NoInspectionAvailable:
        return set()


def existing_unique(table: str) -> set[tuple[str, ...]]:
    if _is_offline():
        return set()
    try:
        return {
            tuple(sorted(constraint["column_names"]))
            for constraint in sa.inspect(op.get_bind()).get_unique_constraints(table)
        }
    except sa.exc.NoInspectionAvailable:
        return set()
