"""Background cleanup service for sessions, crash logs, memory decay, and stale data."""

from __future__ import annotations

import asyncio
import structlog
from datetime import datetime, timezone, timedelta
from pathlib import Path

from app.config import settings

logger = structlog.get_logger()

SESSION_TTL_HOURS = 24 * 7  # 7 days
CRASH_LOG_MAX_AGE_HOURS = 72
CRASH_LOG_MAX_COUNT = 100
MEMORY_DECAY_INTERVAL_HOURS = 24
MEMORY_CLEANUP_INTERVAL_HOURS = 168  # 7 days
MEMORY_ARCHIVE_INTERVAL_HOURS = 168  # 7 days


async def cleanup_expired_sessions() -> int:
    """Remove sessions older than SESSION_TTL_HOURS."""
    try:
        from app.storage import async_session
        from app.storage.database import Session as SessionModel, Message as MessageModel
        from sqlalchemy import delete, select

        cutoff = datetime.now(timezone.utc) - timedelta(hours=SESSION_TTL_HOURS)
        async with async_session() as db:
            old_sessions = (
                await db.execute(select(SessionModel.id).where(SessionModel.created_at < cutoff))
            ).scalars().all()

            if not old_sessions:
                return 0

            session_ids = list(old_sessions)
            await db.execute(delete(MessageModel).where(MessageModel.session_id.in_(session_ids)))
            await db.execute(delete(SessionModel).where(SessionModel.id.in_(session_ids)))
            await db.commit()

            logger.info("sessions_cleaned", count=len(session_ids))
            return len(session_ids)
    except Exception as exc:
        logger.error("session_cleanup_failed", error=str(exc))
        return 0


async def cleanup_crash_logs() -> int:
    """Remove old crash log files and enforce max count."""
    try:
        log_dir = Path(settings.log_dir) / "crashes"
        if not log_dir.exists():
            return 0

        files = sorted(log_dir.glob("crash-*.log"), key=lambda p: p.stat().st_mtime)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=CRASH_LOG_MAX_AGE_HOURS)
        cutoff_ts = cutoff.timestamp()

        removed = 0
        for f in files:
            if f.stat().st_mtime < cutoff_ts:
                f.unlink()
                removed += 1

        # Enforce max count
        remaining = sorted(log_dir.glob("crash-*.log"), key=lambda p: p.stat().st_mtime)
        if len(remaining) > CRASH_LOG_MAX_COUNT:
            for f in remaining[:len(remaining) - CRASH_LOG_MAX_COUNT]:
                f.unlink()
                removed += 1

        if removed:
            logger.info("crash_logs_cleaned", count=removed)
        return removed
    except Exception as exc:
        logger.error("crash_cleanup_failed", error=str(exc))
        return 0


async def cleanup_memory_decay() -> None:
    """Apply memory decay periodically to reduce stale memory relevance."""
    try:
        from app.core.persistent_memory import persistent_memory

        decayed = await persistent_memory.decay_recency_by_access()
        if decayed:
            logger.info("memory_recency_decayed", count=decayed)

        total_pruned = await persistent_memory.cleanup_old_memories(
            user_id="default-user", keep_count=200, min_score=0.01
        )
        if total_pruned:
            logger.info("memory_old_pruned", count=total_pruned)
    except Exception as exc:
        logger.error("memory_decay_failed", error=str(exc))


async def cleanup_memory_archive() -> None:
    """Archive old episodic memories to long-term storage."""
    try:
        from app.core.persistent_memory import persistent_memory
        from app.storage import async_session
        from app.storage.models_memory import EpisodicMemory
        from sqlalchemy import select, func

        # Get all distinct user_ids that have episodic memories
        async with async_session() as db:
            result = await db.execute(
                select(EpisodicMemory.user_id).distinct()
            )
            user_ids = [row[0] for row in result.fetchall()]

        total_archived = 0
        for uid in user_ids:
            stats = await persistent_memory.auto_archive_old_memories(
                user_id=uid, max_episodic_age_days=30, min_importance=0.3
            )
            total_archived += stats.get("archived", 0)

        if total_archived:
            logger.info("memory_archived", count=total_archived)
    except Exception as exc:
        logger.error("memory_archive_failed", error=str(exc))


async def cleanup_task() -> None:
    """Run cleanup periodically."""
    decay_counter = 0
    archive_counter = 0
    while True:
        try:
            await asyncio.sleep(3600)  # Every hour

            await cleanup_expired_sessions()
            await cleanup_crash_logs()

            decay_counter += 1
            if decay_counter >= MEMORY_DECAY_INTERVAL_HOURS:
                decay_counter = 0
                await cleanup_memory_decay()

            archive_counter += 1
            if archive_counter >= MEMORY_ARCHIVE_INTERVAL_HOURS:
                archive_counter = 0
                await cleanup_memory_archive()

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("cleanup_task_error", error=str(exc))


_task: asyncio.Task | None = None


def start_cleanup_task() -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(cleanup_task(), name="cleanup-task")
        logger.info("cleanup_task_started")


def stop_cleanup_task() -> None:
    global _task
    if _task is not None and not _task.done():
        _task.cancel()
    _task = None
