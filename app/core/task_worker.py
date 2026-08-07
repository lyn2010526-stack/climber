"""Task worker — persistent async task execution with progress tracking."""
from __future__ import annotations

import asyncio
import json
import traceback
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import structlog

from app.storage import async_session
from app.storage.models_platform import AutoLoopTask

logger = structlog.get_logger()


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    task_id: str
    task_type: str
    status: TaskStatus
    payload: dict[str, Any]
    result: Any = None
    error: str | None = None
    progress: int = 0
    total_steps: int = 0
    current_step: int = 0
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class TaskManager:
    """Manages task lifecycle: submit, execute, track, cancel."""

    def __init__(self, max_workers: int = 3):
        self._handlers: dict[str, Callable[..., Coroutine]] = {}
        self._semaphore = asyncio.Semaphore(max_workers)
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._progress_callbacks: list[Callable[[str, dict], Coroutine]] = []

    def register(self, task_type: str, handler: Callable[..., Coroutine]) -> None:
        self._handlers[task_type] = handler

    def on_progress(self, callback: Callable[[str, dict], Coroutine]) -> None:
        self._progress_callbacks.append(callback)

    async def submit(self, task_type: str, payload: dict[str, Any]) -> str:
        if task_type not in self._handlers:
            raise ValueError(f"Unknown task type: {task_type}")

        task_id = str(uuid.uuid4())[:12]
        now = datetime.now(UTC)

        async with async_session() as session:
            record = AutoLoopTask(
                id=task_id,
                objective=json.dumps({"type": task_type, **payload}),
                status=TaskStatus.PENDING.value,
                max_steps=payload.get("max_steps", 10),
                current_step=0,
                result=None,
                error=None,
                created_at=now,
                updated_at=now,
                started_at=None,
                finished_at=None,
                heartbeat_at=now,
            )
            session.add(record)
            await session.commit()

        asyncio.create_task(self._run_task(task_id, task_type, payload))
        return task_id

    async def cancel(self, task_id: str) -> bool:
        if task_id in self._active_tasks:
            self._active_tasks[task_id].cancel()
            return True
        return False

    async def get_status(self, task_id: str) -> dict[str, Any] | None:
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if not record:
                return None
            return {
                "task_id": record.id,
                "status": record.status,
                "progress": record.current_step,
                "total_steps": record.max_steps,
                "result": record.result,
                "error": record.error,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "started_at": record.started_at.isoformat() if record.started_at else None,
                "finished_at": record.finished_at.isoformat() if record.finished_at else None,
            }

    async def list_tasks(self, status_filter: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        from sqlalchemy import select
        async with async_session() as session:
            stmt = select(AutoLoopTask).order_by(AutoLoopTask.created_at.desc()).limit(limit)
            if status_filter:
                stmt = stmt.where(AutoLoopTask.status == status_filter)
            result = await session.execute(stmt)
            records = result.scalars().all()
            return [
                {
                    "task_id": r.id,
                    "objective": r.objective[:100],
                    "status": r.status,
                    "progress": r.current_step,
                    "total_steps": r.max_steps,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]

    async def _run_task(self, task_id: str, task_type: str, payload: dict[str, Any]) -> None:
        async with self._semaphore:
            self._active_tasks[task_id] = asyncio.current_task()
            now = datetime.now(UTC)
            handler = self._handlers[task_type]

            async with async_session() as session:
                record = await session.get(AutoLoopTask, task_id)
                if record:
                    record.status = TaskStatus.RUNNING.value
                    record.started_at = now
                    record.heartbeat_at = now
                    await session.commit()

            try:
                async def _progress_cb(step: int, total: int, message: str = ""):
                    async with async_session() as session:
                        rec = await session.get(AutoLoopTask, task_id)
                        if rec:
                            rec.current_step = step
                            rec.max_steps = total
                            rec.heartbeat_at = datetime.now(UTC)
                            await session.commit()
                    await self._emit_progress(task_id, {"step": step, "total": total, "message": message})

                result = await handler(payload=payload, on_progress=_progress_cb)

                async with async_session() as session:
                    record = await session.get(AutoLoopTask, task_id)
                    if record:
                        record.status = TaskStatus.COMPLETED.value
                        record.result = result if isinstance(result, dict) else {"output": str(result)}
                        record.finished_at = datetime.now(UTC)
                        record.current_step = record.max_steps
                        await session.commit()

                await self._emit_progress(task_id, {"status": "completed", "result": result})

            except asyncio.CancelledError:
                async with async_session() as session:
                    record = await session.get(AutoLoopTask, task_id)
                    if record:
                        record.status = TaskStatus.CANCELLED.value
                        record.finished_at = datetime.now(UTC)
                        await session.commit()
                await self._emit_progress(task_id, {"status": "cancelled"})

            except Exception as exc:
                logger.error("task_failed", task_id=task_id, error=str(exc))
                async with async_session() as session:
                    record = await session.get(AutoLoopTask, task_id)
                    if record:
                        record.status = TaskStatus.FAILED.value
                        record.error = str(exc)[:500]
                        record.finished_at = datetime.now(UTC)
                        await session.commit()
                await self._emit_progress(task_id, {"status": "failed", "error": str(exc)})

            finally:
                self._active_tasks.pop(task_id, None)

    async def _emit_progress(self, task_id: str, data: dict) -> None:
        for cb in self._progress_callbacks:
            try:
                await cb(task_id, data)
            except Exception:
                pass


async def handle_agent_run(payload: dict[str, Any], on_progress) -> dict[str, Any]:
    """Execute an autonomous agent run with the given objective."""
    from app.core.agent_engine import AgentEngine
    objective = payload.get("objective", "")
    max_steps = payload.get("max_steps", 10)
    model = payload.get("model")
    engine = AgentEngine()
    result = await engine.run(objective=objective, max_steps=max_steps, model=model, on_progress=on_progress)
    return result


async def handle_data_processing(payload: dict[str, Any], on_progress) -> dict[str, Any]:
    """Process data: transform, filter, aggregate."""
    data = payload.get("data", [])
    operation = payload.get("operation", "identity")
    total = len(data)
    results = []
    for i, item in enumerate(data):
        if operation == "uppercase" and isinstance(item, str):
            results.append(item.upper())
        elif operation == "lowercase" and isinstance(item, str):
            results.append(item.lower())
        elif operation == "reverse":
            results.append(item[::-1] if isinstance(item, str) else item)
        else:
            results.append(item)
        if (i + 1) % max(1, total // 20) == 0:
            await on_progress(i + 1, total, f"Processed {i+1}/{total}")
            await asyncio.sleep(0)
    await on_progress(total, total, "Complete")
    return {"processed": len(results), "results": results[:100]}


async def handle_workflow(payload: dict[str, Any], on_progress) -> dict[str, Any]:
    """Execute a multi-step workflow."""
    from app.multi_agent.flow import Flow
    workflow_name = payload.get("workflow", "default")
    params = payload.get("params", {})
    flow = Flow(name=workflow_name)
    result = await flow.execute(params=params, on_progress=on_progress)
    return result


task_manager = TaskManager(max_workers=3)
task_manager.register("agent_run", handle_agent_run)
task_manager.register("data_processing", handle_data_processing)
task_manager.register("workflow", handle_workflow)


async def run_standalone_worker():
    """Run as standalone worker process."""
    logger.info("standalone_worker_started")
    while True:
        async with async_session() as session:
            from sqlalchemy import select
            stmt = select(AutoLoopTask).where(
                AutoLoopTask.status == TaskStatus.PENDING.value
            ).order_by(AutoLoopTask.created_at).limit(5)
            result = await session.execute(stmt)
            pending = result.scalars().all()
            for record in pending:
                try:
                    obj = json.loads(record.objective)
                    task_type = obj.pop("type", "agent_run")
                    if task_type in task_manager._handlers:
                        await task_manager.submit(task_type, obj)
                except Exception as exc:
                    logger.error("enqueue_failed", task_id=record.id, error=str(exc))
        await asyncio.sleep(5)
