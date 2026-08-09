"""Storage layer - database, cache, vector store.

SQLite is the default backend for local-first operation. Out of the box SQLite
serialises writers and fails fast on contention, which shows up as
"database is locked" under any concurrency. WAL mode plus a busy timeout fixes
that, so the pragmas below are applied to every new connection.
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.config import settings

logger = structlog.get_logger()

db_url = settings.test_database_url if settings.app_testing else settings.database_url

_is_sqlite = db_url.startswith("sqlite")


def _ensure_sqlite_dir(url: str) -> None:
    """Create the parent directory for a file-backed SQLite database."""
    if ":memory:" in url:
        return
    _, _, path_part = url.partition("///")
    if not path_part:
        return
    path = Path(path_part.split("?")[0])
    path.parent.mkdir(parents=True, exist_ok=True)


def _build_engine():
    if _is_sqlite:
        _ensure_sqlite_dir(db_url)
        if ":memory:" in db_url:
            # In-memory needs a single shared connection or each session sees
            # its own empty database.
            return create_async_engine(
                db_url,
                echo=settings.app_debug,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
            )
        return create_async_engine(
            db_url,
            echo=settings.app_debug,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False, "timeout": settings.sqlite_busy_timeout_ms / 1000},
        )

    return create_async_engine(
        db_url,
        echo=settings.app_debug,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,
    )


engine = _build_engine()


if _is_sqlite:

    @event.listens_for(engine.sync_engine, "connect")
    def _apply_sqlite_pragmas(dbapi_connection, connection_record):  # noqa: ANN001
        """WAL + tuning pragmas, applied per connection."""
        cursor = dbapi_connection.cursor()
        try:
            if settings.sqlite_wal:
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute(f"PRAGMA busy_timeout={settings.sqlite_busy_timeout_ms}")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA cache_size=-64000")  # 64 MB page cache
            cursor.execute("PRAGMA temp_store=MEMORY")
        except Exception as exc:  # pragma: no cover - pragma failure is non-fatal
            logger.warning("sqlite_pragma_failed", error=str(exc))
        finally:
            cursor.close()


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> Any:
    """FastAPI dependency: yield a database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as exc:
            logger.warning("storage.get_db_session_failed", error=str(exc))
            await session.rollback()
            raise


async def db_health() -> dict[str, Any]:
    """Report backend, journal mode and connectivity for diagnostics."""
    info: dict[str, Any] = {"backend": "sqlite" if _is_sqlite else "other", "url": db_url.split("://")[0]}
    from sqlalchemy.exc import OperationalError

    for attempt in range(3):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                info["connected"] = True
                if _is_sqlite:
                    mode = await conn.execute(text("PRAGMA journal_mode"))
                    info["journal_mode"] = mode.scalar()
                    busy = await conn.execute(text("PRAGMA busy_timeout"))
                    info["busy_timeout_ms"] = busy.scalar()
            return info
        except OperationalError as exc:
            if "locked" in str(exc).lower() and attempt < 2:
                await asyncio.sleep(0.05 * (attempt + 1))
                continue
            info["connected"] = False
            info["error"] = str(exc)
            return info
        except Exception as exc:
            info["connected"] = False
            info["error"] = str(exc)
            return info
    return info


async def init_db() -> None:
    """Create all tables. Ensure all models are imported for registration."""
    # Import all models so SQLAlchemy registers them with Base
    from app.models import users as _users_model  # noqa: F401
    from app.storage import (
        database,  # noqa: F401
        models_cost,  # noqa: F401
        models_eval,  # noqa: F401
        models_feedback,  # noqa: F401
        models_files,  # noqa: F401
        models_groups,  # noqa: F401
        models_memory,  # noqa: F401
        models_platform,  # noqa: F401
        models_plugins,  # noqa: F401
        models_reasoning,  # noqa: F401
        models_skills,  # noqa: F401
        models_traces,  # noqa: F401
    )

    async with engine.begin() as conn:
        with contextlib.suppress(Exception):
            await conn.run_sync(Base.metadata.create_all)
