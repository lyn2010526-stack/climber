"""Task worker — persistent async task execution with progress tracking."""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from collections import OrderedDict, defaultdict, deque
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from functools import partial
from typing import Any, cast

import structlog
from sqlalchemy import CursorResult

from app.config import settings
from app.core.execution.event_bus import EventBus, TaskEvent
from app.storage import async_session
from app.storage.models_platform import AutoLoopTask

logger = structlog.get_logger()

_SENSITIVE_PAYLOAD_KEYS = {"api_key", "api_key_encrypted"}
_SUBTASK_STATUSES = {
    "pending",
    "ready",
    "claimed",
    "running",
    "retrying",
    "completed",
    "failed",
    "blocked",
    "skipped",
    "dead_letter",
}


async def resolve_owner_agent_payload(
    owner_id: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Resolve credentials only from the task owner's active stored configuration."""
    from sqlalchemy import select

    from app.core.api_key_crypto import decrypt_api_key
    from app.storage.database import Agent, ApiKey

    if not owner_id or not owner_id.strip():
        raise ValueError("Task owner is required")
    payload = dict(payload or {})
    async with async_session() as db:
        query = select(Agent).where(Agent.user_id == owner_id, Agent.is_active)
        if payload.get("provider"):
            query = query.where(Agent.provider == payload["provider"])
        if payload.get("model"):
            query = query.where(Agent.model_id == payload["model"])
        agent = await db.scalar(query.order_by(Agent.created_at.desc(), Agent.id))
        provider = payload.get("provider") or (agent.provider if agent else None)
        model = payload.get("model") or (agent.model_id if agent else None)
        if not provider or not model:
            raise ValueError("Task owner has no active model configuration")
        stored_key = agent.api_key_encrypted if agent else None
        base_url = agent.base_url if agent else None
        if not stored_key:
            key = await db.scalar(
                select(ApiKey)
                .where(ApiKey.user_id == owner_id, ApiKey.provider == provider, ApiKey.is_active)
                .order_by(ApiKey.created_at.desc(), ApiKey.id)
            )
            if key:
                stored_key = key.api_key_encrypted
                base_url = key.base_url or base_url
        try:
            api_key = decrypt_api_key(stored_key) if stored_key else ""
        except Exception:
            raise ValueError("Task owner credential cannot be decrypted") from None
        if not api_key and provider != "ollama":
            raise ValueError("Task owner has no active provider credential")
        if provider == "ollama" and not base_url:
            raise ValueError("Task owner local model requires a configured endpoint")
        payload.pop("api_key_encrypted", None)
        return {
            **payload,
            "user_id": owner_id,
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "base_url": base_url,
            "system_prompt": payload.get(
                "system_prompt", agent.system_prompt or "" if agent else ""
            ),
            "tools": payload.get("tools", list(agent.tool_ids or []) if agent else []),
        }


async def _ensure_task_control_columns() -> None:
    """Upgrade legacy local task tables before using durable controls."""
    from sqlalchemy import text

    columns = {
        "retry_count": "INTEGER DEFAULT 0",
        "interruption_reason": "VARCHAR(40)",
        "checkpoint": "JSON",
        "progress_evaluation": "JSON",
    }
    async with async_session() as session:
        for name, definition in columns.items():
            with suppress(Exception):
                await session.execute(
                    text(f"ALTER TABLE auto_loop_tasks ADD COLUMN {name} {definition}")
                )
        await session.commit()


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RETRYING = "retrying"


def _lease_expired(value: Any, now_timestamp: float) -> bool:
    try:
        return float(value or 0) <= now_timestamp
    except (TypeError, ValueError):
        return True


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

    def __init__(
        self,
        max_workers: int | None = None,
        max_task_retries: int = 2,
        event_bus: EventBus | None = None,
    ):
        self._handlers: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}
        self._max_workers = settings.max_concurrent_subtasks if max_workers is None else max_workers
        self._max_task_retries = max(0, max_task_retries)
        self._max_claim_attempts = 3
        self._semaphore = asyncio.Semaphore(self._max_workers)
        self._active_tasks: dict[str, asyncio.Task[Any]] = {}
        self._progress_callbacks: list[
            Callable[[str, dict[str, Any]], Coroutine[Any, Any, Any]]
        ] = []
        self._event_history: OrderedDict[str, deque[dict[str, Any]]] = OrderedDict()
        self._event_subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._event_epoch = str(uuid.uuid4())
        self._event_sequence = 0
        self._event_ids: dict[str, str] = {}
        self._event_bus = event_bus

    @property
    def max_workers(self) -> int:
        return self._max_workers

    @property
    def max_task_retries(self) -> int:
        return self._max_task_retries

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        """Hold one execution slot so parallel task runs stay within the limit."""
        async with self._semaphore:
            yield

    def register(self, task_type: str, handler: Callable[..., Coroutine[Any, Any, Any]]) -> None:
        self._handlers[task_type] = handler

    def on_progress(
        self, callback: Callable[[str, dict[str, Any]], Coroutine[Any, Any, Any]]
    ) -> None:
        self._progress_callbacks.append(callback)

    def subscribe(self, task_id: str, *, replay: bool = True) -> asyncio.Queue[dict[str, Any]]:
        """Subscribe to task-specific lifecycle events, replaying recent history."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        for event in self._event_history.get(task_id, ()) if replay else ():
            queue.put_nowait(event)
        self._event_subscribers[task_id].add(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        subscribers = self._event_subscribers.get(task_id)
        if subscribers is None:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._event_subscribers.pop(task_id, None)
            while len(self._event_history) > 100:
                self._event_history.popitem(last=False)

    @staticmethod
    def _validate_subtask_graph(subtasks: list[dict[str, Any]]) -> None:
        ids = [str(item.get("id", "")) for item in subtasks]
        if len(ids) != len(set(ids)):
            raise ValueError("Subtask IDs must be unique")
        known = set(ids)
        graph = {item_id: set() for item_id in ids}
        for item in subtasks:
            item_id = str(item.get("id", ""))
            dependencies = item.get("dependencies", [])
            if not isinstance(dependencies, list) or any(
                not isinstance(dependency, str) for dependency in dependencies
            ):
                raise ValueError("Subtask dependencies must be a list of IDs")
            if item_id in dependencies:
                raise ValueError("A subtask cannot depend on itself")
            missing = set(dependencies) - known
            if missing:
                raise ValueError("Subtask dependencies must reference a subtask in the same task")
            graph[item_id].update(dependencies)
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError("Subtask dependencies cannot contain cycles")
            if node in visited:
                return
            visiting.add(node)
            for dependency in graph[node]:
                visit(dependency)
            visiting.remove(node)
            visited.add(node)

        for node in graph:
            visit(node)

    async def emit_event(self, task_id: str, event_type: str, data: dict[str, Any]) -> None:
        event_id = str(uuid.uuid4())
        causation_id = self._event_ids.get(task_id)
        timestamp = datetime.now(UTC).isoformat()
        bus = self._event_bus
        if bus is None:
            from app.core.execution.event_bus import get_task_event_bus

            bus = get_task_event_bus()
            self._event_bus = bus
        persisted = TaskEvent(
            event_id=event_id,
            event_type=event_type,
            task_id=task_id,
            timestamp=timestamp,
            data=data,
            schema_version=1,
            correlation_id=task_id,
            causation_id=causation_id,
            producer="task_manager",
        )
        await bus.publish(persisted)
        self._event_sequence = max(self._event_sequence, persisted.sequence or 0)
        event = {
            "event_id": event_id,
            "type": event_type,
            "data": data,
            "task_id": task_id,
            "sequence": persisted.sequence,
            "epoch": self._event_epoch,
            "timestamp": timestamp,
            "protocol_version": 1,
            "schema_version": 1,
            "correlation_id": task_id,
            "causation_id": causation_id,
            "producer": "task_manager",
        }
        self._event_ids[task_id] = event_id
        history = self._event_history.setdefault(task_id, deque(maxlen=100))
        history.append(event)
        self._event_history.move_to_end(task_id)
        while len(self._event_history) > 100:
            removable = next(
                (
                    history_task_id
                    for history_task_id in self._event_history
                    if not self._event_subscribers.get(history_task_id)
                ),
                None,
            )
            if removable is None:
                break
            self._event_history.pop(removable, None)
        for queue in tuple(self._event_subscribers.get(task_id, ())):
            queue.put_nowait(event)

    async def event_snapshot(
        self, task_id: str, owner_id: str, include_all: bool = False
    ) -> dict[str, Any] | None:
        sequence = self._event_sequence
        history = list(self._event_history.get(task_id, ()))
        state = await self.get_status(task_id, owner_id=owner_id, include_all=include_all)
        if state is None:
            return None
        return {
            "type": "snapshot",
            "task_id": task_id,
            "protocol_version": 1,
            "epoch": self._event_epoch,
            "sequence": sequence,
            "data": state,
            "events": history,
            "history_scope": "process_recent_100",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def submit(
        self, task_type: str, payload: dict[str, Any], owner_id: str = "default-user"
    ) -> str:
        if task_type not in self._handlers:
            raise ValueError(f"Unknown task type: {task_type}")
        if not owner_id or not owner_id.strip():
            raise ValueError("Task owner is required")
        payload = {**payload, "user_id": owner_id}
        if "subtasks" in payload:
            normalized_subtasks = []
            for index, item in enumerate(payload["subtasks"] or [], start=1):
                if not isinstance(item, dict) or not str(item.get("description", "")).strip():
                    raise ValueError("Each subtask requires a non-empty description")
                normalized_subtasks.append(
                    {
                        **item,
                        "id": str(item.get("id") or f"st-{index}"),
                        "status": "pending",
                        "dependencies": list(item.get("dependencies") or []),
                        "result": None,
                        "error": "",
                        "claim_token": None,
                        "lease_version": 0,
                        "attempt": 0,
                        "worker_id": None,
                        "heartbeat_at": None,
                        "completion_id": None,
                    }
                )
            self._validate_subtask_graph(normalized_subtasks)
            payload["subtasks"] = normalized_subtasks

        task_id = str(uuid.uuid4())[:12]
        now = datetime.now(UTC)
        await _ensure_task_control_columns()

        async with async_session() as session:
            persisted_payload = {
                key: value for key, value in payload.items() if key not in _SENSITIVE_PAYLOAD_KEYS
            }
            record = AutoLoopTask(
                id=task_id,
                owner_id=owner_id,
                objective=json.dumps({**persisted_payload, "type": task_type}),
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

        # Fresh submissions deliberately keep ``resolve_credentials=False``:
        # the caller just supplied the model config (provider/model/api_key)
        # in the request payload, and ``handle_agent_run`` consumes exactly
        # that payload. Stored-owner config is only resolved on the
        # recover/resume/retry paths, where the original request credentials
        # are unavailable (wave-2 R9-10 design decision).
        worker = asyncio.create_task(self._run_task(task_id, task_type, payload, managed=True))
        self._active_tasks[task_id] = worker
        worker.add_done_callback(lambda done: self._release_worker(task_id, done))
        return task_id

    async def recover_pending_tasks(self, limit: int = 5) -> int:
        """Queue only never-started TaskManager envelopes, retaining ID and owner.

        Running/retrying rows require manual review: there is no durable tool
        checkpoint or lease proving safe replay. AutoLoop rows are left alone.
        """
        from sqlalchemy import select

        queued = 0
        ready: list[tuple[str, str, dict[str, Any]]] = []
        async with async_session() as session:
            rows = (
                await session.scalars(
                    select(AutoLoopTask)
                    .where(AutoLoopTask.status == TaskStatus.PENDING.value)
                    .order_by(AutoLoopTask.created_at)
                )
            ).all()
            for record in rows:
                if len(ready) >= limit:
                    break
                if record.id in self._active_tasks:
                    continue
                try:
                    payload = json.loads(record.objective)
                except (TypeError, ValueError):
                    continue
                if not isinstance(payload, dict) or "type" not in payload:
                    continue
                task_type = payload.pop("type")
                if (
                    task_type in self._handlers
                    and record.owner_id
                    and record.interruption_reason in {"resumed", "retry", "rollback"}
                    and record.started_at is None
                    and record.finished_at is None
                ):
                    record.status = TaskStatus.PAUSED.value
                    record.error = "Queued control interrupted by restart; explicit resume and checkpoint review required"
                    continue
                if (
                    not isinstance(task_type, str)
                    or task_type not in self._handlers
                    or not record.owner_id
                    or not record.owner_id.strip()
                    or record.started_at
                    or record.current_step
                    or record.finished_at
                    or record.result is not None
                    or record.error
                ):
                    record.status = TaskStatus.FAILED.value
                    record.error = "Automatic recovery refused: invalid configuration or prior execution; manual review required"
                    record.finished_at = datetime.now(UTC)
                    continue
                ready.append((record.id, task_type, payload))
            await session.commit()
        for task_id, task_type, payload in ready:
            if task_id in self._active_tasks:
                continue
            # Recovery path: the original request credentials are gone (the
            # persisted envelope strips api_key), so resolve the task owner's
            # stored model configuration before dispatch.
            worker = asyncio.create_task(
                self._run_task(task_id, task_type, payload, resolve_credentials=True, managed=True)
            )
            self._active_tasks[task_id] = worker
            worker.add_done_callback(partial(self._release_worker, task_id))
            queued += 1
        return queued

    async def cancel(self, task_id: str) -> bool:
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if record is None or record.status in {
                TaskStatus.COMPLETED.value,
                TaskStatus.FAILED.value,
                TaskStatus.CANCELLED.value,
            }:
                return False
            record.status = TaskStatus.CANCELLED.value
            record.interruption_reason = "cancelled"
            record.finished_at = datetime.now(UTC)
            await session.commit()
        task = self._active_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
        await self._emit_progress(
            task_id, {"status": TaskStatus.CANCELLED.value, "reason": "cancelled"}
        )
        return True

    async def pause(self, task_id: str) -> bool:
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if record is None or record.status not in {
                TaskStatus.PENDING.value,
                TaskStatus.RUNNING.value,
                TaskStatus.RETRYING.value,
            }:
                return False
            record.status = TaskStatus.PAUSED.value
            record.interruption_reason = "paused"
            record.updated_at = datetime.now(UTC)
            await session.commit()
        task = self._active_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
        await self._emit_progress(task_id, {"status": TaskStatus.PAUSED.value, "reason": "paused"})
        return True

    async def resume(self, task_id: str) -> bool:
        return await self._requeue(task_id, {TaskStatus.PAUSED.value}, "resumed")

    async def retry(self, task_id: str) -> bool:
        return await self._requeue(
            task_id, {TaskStatus.FAILED.value, TaskStatus.CANCELLED.value}, "retry"
        )

    async def rollback(self, task_id: str) -> bool:
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if record is None or not record.checkpoint:
                return False
            worker = self._active_tasks.get(task_id)
            if record.status in {
                TaskStatus.PENDING.value,
                TaskStatus.RUNNING.value,
                TaskStatus.RETRYING.value,
            } or (worker is not None and not worker.done()):
                raise ValueError(
                    "Rollback requires a stopped worker; pause and await worker exit first"
                )
            checkpoint = dict(record.checkpoint)
            record.current_step = int(checkpoint.get("step", 0))
            record.progress_evaluation = checkpoint.get("evaluation")
            record.status = TaskStatus.PENDING.value
            record.finished_at = None
            record.interruption_reason = "rollback"
            record.updated_at = datetime.now(UTC)
            await session.commit()
        return await self._requeue(task_id, {TaskStatus.PENDING.value}, "rollback")

    async def _requeue(self, task_id: str, allowed: set[str], reason: str) -> bool:
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if record is None or record.status not in allowed:
                return False
            try:
                envelope = json.loads(record.objective)
                if not isinstance(envelope, dict):
                    return False
                task_type = envelope.pop("type")
            except (TypeError, ValueError, KeyError):
                return False
            if task_type not in self._handlers:
                return False
            if task_type == "factory_run" and (
                record.started_at
                or record.current_step
                or record.checkpoint is not None
                or record.interruption_reason in {"resumed", "retry", "rollback"}
            ):
                envelope["_factory_checkpoint"] = record.checkpoint or {}
                record.checkpoint = envelope["_factory_checkpoint"]
            # Revoke the old run before publishing the new pending state.
            self._active_tasks.pop(task_id, None)
            record.status = TaskStatus.PENDING.value
            record.finished_at = None
            record.started_at = None
            record.error = None
            record.result = None
            if reason != "rollback" and task_type != "factory_run":
                record.current_step = 0
            record.interruption_reason = reason
            record.retry_count = (record.retry_count or 0) + (reason == "retry")
            record.updated_at = datetime.now(UTC)
            await session.commit()
        # Resume/retry control path: same rationale as recover_pending_tasks —
        # stored-owner model config is resolved because the caller no longer
        # supplies request credentials.
        worker = asyncio.create_task(
            self._run_task(task_id, task_type, envelope, resolve_credentials=True, managed=True)
        )
        self._active_tasks[task_id] = worker
        worker.add_done_callback(lambda done: self._release_worker(task_id, done))
        await self._emit_progress(
            task_id,
            {
                "status": "pending",
                "control": reason,
                "retry_count": record.retry_count if "record" in locals() else 0,
            },
        )
        return True

    async def get_status(
        self, task_id: str, owner_id: str | None = None, include_all: bool = False
    ) -> dict[str, Any] | None:
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if not record:
                return None
            if owner_id is not None and not include_all and record.owner_id != owner_id:
                return None
            return {
                "task_id": record.id,
                "objective": self._objective_from_record(record.objective),
                "status": record.status,
                "progress": record.current_step,
                "total_steps": record.max_steps,
                "result": record.result,
                "error": record.error,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "started_at": record.started_at.isoformat() if record.started_at else None,
                "finished_at": record.finished_at.isoformat() if record.finished_at else None,
                "retry_count": record.retry_count or 0,
                "checkpoint": record.checkpoint,
                "progress_evaluation": record.progress_evaluation,
                "interruption_reason": record.interruption_reason,
            }

    @staticmethod
    def _objective_from_record(raw_objective: str) -> str:
        try:
            payload = json.loads(raw_objective)
        except (TypeError, json.JSONDecodeError):
            return raw_objective
        if not isinstance(payload, dict):
            return str(payload) or ""
        return str(payload.get("objective") or payload.get("workflow") or payload.get("type") or "")

    async def list_tasks(
        self,
        status_filter: str | None = None,
        limit: int = 50,
        owner_id: str | None = None,
        include_all: bool = False,
    ) -> list[dict[str, Any]]:
        from sqlalchemy import select

        async with async_session() as session:
            stmt = select(AutoLoopTask).order_by(AutoLoopTask.created_at.desc())
            if status_filter:
                stmt = stmt.where(AutoLoopTask.status == status_filter)
            if owner_id is not None and not include_all:
                stmt = stmt.where(AutoLoopTask.owner_id == owner_id)
            stmt = stmt.limit(limit)
            result = await session.execute(stmt)
            records = result.scalars().all()
            return [
                {
                    "task_id": r.id,
                    "objective": self._objective_from_record(r.objective)[:100],
                    "status": r.status,
                    "progress": r.current_step,
                    "total_steps": r.max_steps,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "retry_count": r.retry_count or 0,
                    "progress_evaluation": r.progress_evaluation,
                    "error": r.error,
                    "interruption_reason": r.interruption_reason,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                }
                for r in records
            ]

    @staticmethod
    def _subtasks_from_record(record: AutoLoopTask) -> list[dict[str, Any]]:
        """Read the normalized subtask queue embedded in a task envelope."""
        try:
            envelope = json.loads(record.objective)
        except (TypeError, json.JSONDecodeError):
            return []
        subtasks = envelope.get("subtasks", []) if isinstance(envelope, dict) else []
        return subtasks if isinstance(subtasks, list) else []

    async def list_subtasks(
        self,
        task_id: str,
        *,
        owner_id: str,
        include_all: bool = False,
        status: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """Return a task's dependency-aware subtask queue."""
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if record is None or (not include_all and record.owner_id != owner_id):
                return None
            subtasks = self._subtasks_from_record(record)
            return [item for item in subtasks if status is None or item.get("status") == status]

    async def claim_subtasks(
        self,
        task_id: str,
        *,
        owner_id: str,
        agent_id: str,
        limit: int = 1,
        include_all: bool = False,
        lease_seconds: int = 900,
        worker_id: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """Atomically claim ready subtasks for a worker agent.

        Subtasks are stored in the parent envelope so claims survive process
        restarts without introducing a second queue database or a second task ID.
        """
        from sqlalchemy import update

        now = datetime.now(UTC)
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if record is None or (not include_all and record.owner_id != owner_id):
                return None
            original = record.objective
            try:
                envelope = json.loads(original)
            except (TypeError, json.JSONDecodeError):
                return []
            if not isinstance(envelope, dict):
                return []
            subtasks = envelope.get("subtasks", [])
            if not isinstance(subtasks, list):
                return []
            # A crashed agent must not strand work in the claimed state.
            now_timestamp = now.timestamp()
            lease_reclaimed = False
            for item in subtasks:
                if item.get("status") == "claimed" and _lease_expired(
                    item.get("lease_expires_at"), now_timestamp
                ):
                    lease_reclaimed = True
                    item.update(
                        {
                            "status": "pending",
                            "claimed_by": None,
                            "claimed_at": None,
                            "lease_expires_at": None,
                            "claim_token": None,
                            "worker_id": None,
                        }
                    )
            completed = {item.get("id") for item in subtasks if item.get("status") == "completed"}
            claimed: list[dict[str, Any]] = []
            for item in subtasks:
                dependencies = set(item.get("dependencies", []))
                if (
                    len(claimed) >= limit
                    or item.get("status") != "pending"
                    or not dependencies.issubset(completed)
                ):
                    continue
                item.update(
                    {
                        "status": "claimed",
                        "claimed_by": agent_id,
                        "claimed_at": now.isoformat(),
                        "lease_expires_at": (now_timestamp + max(1, lease_seconds)),
                        "claim_token": str(uuid.uuid4()),
                        "lease_version": int(item.get("lease_version") or 0) + 1,
                        "attempt": int(item.get("attempt") or 0) + 1,
                        "worker_id": worker_id or agent_id,
                        "heartbeat_at": now.isoformat(),
                    }
                )
                claimed.append(dict(item))
            if not claimed and not lease_reclaimed:
                return []
            envelope["subtasks"] = subtasks
            updated = await session.execute(
                update(AutoLoopTask)
                .where(
                    AutoLoopTask.id == task_id,
                    AutoLoopTask.owner_id == record.owner_id,
                    AutoLoopTask.objective == original,
                )
                .values(objective=json.dumps(envelope, ensure_ascii=False), updated_at=now)
            )
            if cast(CursorResult[Any], updated).rowcount != 1:
                return []
            await session.commit()
        await self._emit_progress(
            task_id,
            {
                "status": "subtasks_claimed",
                "count": len(claimed),
                "agent_id": agent_id,
                "subtask_ids": [item.get("id") for item in claimed],
                "lease_reclaimed": lease_reclaimed,
            },
        )
        return claimed

    async def complete_subtask(
        self,
        task_id: str,
        subtask_id: str,
        *,
        owner_id: str,
        agent_id: str,
        result: Any = None,
        error: str | None = None,
        include_all: bool = False,
        claim_token: str | None = None,
        lease_version: int | None = None,
        completion_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Complete a claimed subtask and make dependent work claimable."""
        from sqlalchemy import update

        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if record is None or (not include_all and record.owner_id != owner_id):
                return None
            original = record.objective
            try:
                envelope = json.loads(original)
            except (TypeError, json.JSONDecodeError):
                return None
            if not isinstance(envelope, dict):
                return None
            subtasks = envelope.get("subtasks", [])
            target = next((item for item in subtasks if item.get("id") == subtask_id), None)
            if target is None or target.get("claimed_by") != agent_id:
                return None
            if completion_id and target.get("completion_id") == completion_id:
                if (
                    (claim_token is None or target.get("claim_token") == claim_token)
                    and (lease_version is None or target.get("lease_version") == lease_version)
                    and target.get("status") in {"running", "completed", "failed"}
                ):
                    return dict(target)
                return None
            if (
                target.get("status") not in {"claimed", "running"}
                or (claim_token is not None and target.get("claim_token") != claim_token)
                or (lease_version is not None and target.get("lease_version") != lease_version)
                or _lease_expired(target.get("lease_expires_at"), datetime.now(UTC).timestamp())
            ):
                return None
            target.update(
                {
                    "status": "failed" if error else "completed",
                    "result": result,
                    "error": error or "",
                    "completed_at": datetime.now(UTC).isoformat(),
                    "lease_expires_at": None,
                    "completion_id": completion_id,
                }
            )
            completed_count = sum(item.get("status") == "completed" for item in subtasks)
            failed = any(item.get("status") == "failed" for item in subtasks)
            has_unfinished = any(item.get("status") in {"pending", "claimed"} for item in subtasks)
            if failed:
                record.status = TaskStatus.FAILED.value
                record.error = "A subtask failed"
                record.finished_at = datetime.now(UTC)
            elif not has_unfinished and subtasks:
                record.status = TaskStatus.COMPLETED.value
                record.finished_at = datetime.now(UTC)
            elif record.status == TaskStatus.PENDING.value:
                record.status = TaskStatus.RUNNING.value
                record.started_at = record.started_at or datetime.now(UTC)
            record.current_step = completed_count
            record.max_steps = len(subtasks)
            record.progress_evaluation = {
                "percent": round(completed_count / len(subtasks) * 100, 2),
                "message": "Subtasks complete" if not has_unfinished else "Subtasks in progress",
                "step": completed_count,
                "total": len(subtasks),
            }
            envelope["subtasks"] = subtasks
            updated = await session.execute(
                update(AutoLoopTask)
                .where(
                    AutoLoopTask.id == task_id,
                    AutoLoopTask.owner_id == record.owner_id,
                    AutoLoopTask.objective == original,
                )
                .values(
                    objective=json.dumps(envelope, ensure_ascii=False), updated_at=datetime.now(UTC)
                )
            )
            if cast(CursorResult[Any], updated).rowcount != 1:
                return None
            await session.commit()
        await self._emit_progress(
            task_id,
            {
                "status": "subtask_completed",
                "subtask_id": subtask_id,
                "parent_status": record.status,
                "progress": record.current_step,
                "total": record.max_steps,
                "completed_count": completed_count,
                "remaining_count": sum(
                    item.get("status") in {"pending", "claimed"} for item in subtasks
                ),
            },
        )
        return dict(target)

    async def heartbeat_subtask(
        self,
        task_id: str,
        subtask_id: str,
        *,
        owner_id: str,
        agent_id: str,
        claim_token: str,
        lease_version: int,
        extend_seconds: int = 300,
        include_all: bool = False,
    ) -> dict[str, Any] | None:
        """Extend a live subtask lease using its fencing token."""
        from sqlalchemy import update

        now = datetime.now(UTC)
        now_timestamp = now.timestamp()
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if record is None or (not include_all and record.owner_id != owner_id):
                return None
            original = record.objective
            try:
                envelope = json.loads(original)
            except (TypeError, json.JSONDecodeError):
                return None
            subtasks = envelope.get("subtasks", []) if isinstance(envelope, dict) else []
            target = next((item for item in subtasks if item.get("id") == subtask_id), None)
            if (
                target is None
                or target.get("status") not in {"claimed", "running"}
                or target.get("claimed_by") != agent_id
                or target.get("claim_token") != claim_token
                or target.get("lease_version") != lease_version
                or _lease_expired(target.get("lease_expires_at"), now_timestamp)
            ):
                return None
            target["status"] = "running"
            target["heartbeat_at"] = now.isoformat()
            current_expiry = float(target.get("lease_expires_at") or now_timestamp)
            target["lease_expires_at"] = max(current_expiry, now_timestamp) + max(1, extend_seconds)
            envelope["subtasks"] = subtasks
            updated = await session.execute(
                update(AutoLoopTask)
                .where(
                    AutoLoopTask.id == task_id,
                    AutoLoopTask.owner_id == record.owner_id,
                    AutoLoopTask.objective == original,
                )
                .values(objective=json.dumps(envelope, ensure_ascii=False), updated_at=now)
            )
            if cast(CursorResult[Any], updated).rowcount != 1:
                return None
            await session.commit()
        await self._emit_progress(
            task_id,
            {
                "status": "subtask_heartbeat",
                "subtask_id": subtask_id,
                "agent_id": agent_id,
                "lease_version": lease_version,
                "lease_expires_at": target["lease_expires_at"],
            },
        )
        return dict(target)

    def _owns_worker(self, task_id: str, worker: asyncio.Task[Any] | None) -> bool:
        return worker is None or self._active_tasks.get(task_id) is worker

    def _release_worker(self, task_id: str, worker: asyncio.Task[Any]) -> None:
        if self._active_tasks.get(task_id) is worker:
            self._active_tasks.pop(task_id, None)

    async def _run_task(
        self,
        task_id: str,
        task_type: str,
        payload: dict[str, Any],
        *,
        resolve_credentials: bool = False,
        managed: bool = False,
    ) -> None:
        """Execute one claimed task row.

        ``resolve_credentials`` is set by the recover/resume/retry dispatchers
        only; fresh submissions keep the request-supplied credentials (R9-10
        wave-2 contract, see ``submit``).
        """
        from sqlalchemy import update

        worker = asyncio.current_task() if managed else None
        async with self.slot():
            if not self._owns_worker(task_id, worker):
                return
            now = datetime.now(UTC)
            handler = self._handlers[task_type]

            owner_id = ""
            claim_attempts = max(1, self._max_claim_attempts)
            for claim_attempt in range(1, claim_attempts + 1):
                try:
                    async with async_session() as session:
                        record = await session.get(AutoLoopTask, task_id)
                        if record is None:
                            return
                        try:
                            envelope = json.loads(record.objective)
                        except (TypeError, ValueError):
                            return
                        if not isinstance(envelope, dict) or envelope.get("type") != task_type:
                            return
                        owner_id = record.owner_id
                        if task_type == "factory_run" and record.checkpoint is not None:
                            payload = {**payload, "_factory_checkpoint": record.checkpoint}
                        if not self._owns_worker(task_id, worker):
                            return
                        claimed = await session.execute(
                            update(AutoLoopTask)
                            .where(
                                AutoLoopTask.id == task_id,
                                AutoLoopTask.owner_id == owner_id,
                                AutoLoopTask.objective == record.objective,
                                AutoLoopTask.status == TaskStatus.PENDING.value,
                                AutoLoopTask.started_at.is_(None),
                                AutoLoopTask.finished_at.is_(None),
                            )
                            .values(
                                status=TaskStatus.RUNNING.value, started_at=now, heartbeat_at=now
                            )
                        )
                        await session.commit()
                    if cast(CursorResult[Any], claimed).rowcount == 1:
                        break
                    return
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning(
                        "task_claim_retry", task_id=task_id, attempt=claim_attempt, error=str(exc)
                    )
                    if claim_attempt < claim_attempts:
                        await asyncio.sleep(0.1 * claim_attempt)
                        continue
                    async with async_session() as session:
                        record = await session.get(AutoLoopTask, task_id)
                        if record is not None and record.status == TaskStatus.PENDING.value:
                            record.status = TaskStatus.FAILED.value
                            record.error = (
                                f"Task claim failed ({type(exc).__name__}); manual review required"
                            )
                            record.finished_at = datetime.now(UTC)
                            await session.commit()
                    await self._emit_progress(
                        task_id, {"status": TaskStatus.FAILED.value, "error": "claim failed"}
                    )
                    return

            await self._emit_progress(task_id, {"status": TaskStatus.RUNNING.value})
            try:

                async def _progress_cb(step: int, total: int, message: str = "") -> None:
                    await self._persist_progress(task_id, step, total, message, worker=worker)

                if resolve_credentials and task_type in {"agent_run", "factory_run"}:
                    payload = await resolve_owner_agent_payload(owner_id, payload)
                runtime_payload = {**payload, "user_id": owner_id, "_task_id": task_id}
                if task_type == "factory_run":

                    async def save_factory_checkpoint(snapshot: dict[str, Any]) -> None:
                        from app.core.checkpoint import CheckpointData, sanitize_checkpoint

                        safe = sanitize_checkpoint(
                            CheckpointData(
                                session_id=task_id,
                                messages=[],
                                iteration=0,
                                status="running",
                                channel_values={"factory": snapshot},
                            ),
                            secrets=(str(runtime_payload.get("api_key", "")),),
                        ).channel_values["factory"]
                        safe["recovery_blocked"] = (
                            safe["plan"] != snapshot["plan"]
                            or safe["results"] != snapshot["results"]
                        )
                        safe["plan_digest"] = hashlib.sha256(
                            json.dumps(safe["plan"], sort_keys=True).encode()
                        ).hexdigest()
                        async with async_session() as db:
                            row = await db.get(AutoLoopTask, task_id)
                            if (
                                not self._owns_worker(task_id, worker)
                                or row is None
                                or row.status
                                not in {TaskStatus.RUNNING.value, TaskStatus.RETRYING.value}
                            ):
                                raise asyncio.CancelledError
                            row.checkpoint = {**(row.checkpoint or {}), "factory": safe}
                            row.heartbeat_at = datetime.now(UTC)
                            await db.commit()

                    runtime_payload["_save_factory_checkpoint"] = save_factory_checkpoint
                if not self._owns_worker(task_id, worker):
                    return
                result = await handler(payload=runtime_payload, on_progress=_progress_cb)
                result_status = (
                    TaskStatus.FAILED.value
                    if isinstance(result, dict) and result.get("status") == TaskStatus.FAILED.value
                    else TaskStatus.COMPLETED.value
                )

                async with async_session() as session:
                    record = await session.get(AutoLoopTask, task_id)
                    subtasks = self._subtasks_from_record(record) if record else []
                    subtasks_pending = any(
                        item.get("status") in {"pending", "claimed"} for item in subtasks
                    )
                    subtask_failed = any(item.get("status") == "failed" for item in subtasks)
                    if (
                        self._owns_worker(task_id, worker)
                        and record
                        and record.status == TaskStatus.RUNNING.value
                    ):
                        if subtask_failed:
                            result_status = TaskStatus.FAILED.value
                            record.error = "A subtask failed"
                        elif subtasks_pending:
                            result_status = TaskStatus.RUNNING.value
                            record.error = None
                        record.status = result_status
                        record.result = (
                            result if isinstance(result, dict) else {"output": str(result)}
                        )
                        if result_status == TaskStatus.FAILED.value and isinstance(result, dict):
                            record.error = str(result.get("error", ""))[:500]
                        record.finished_at = (
                            None if result_status == TaskStatus.RUNNING.value else datetime.now(UTC)
                        )
                        await session.commit()
                    else:
                        return

                await self._emit_progress(task_id, {"status": result_status, "result": result})

            except asyncio.CancelledError:
                async with async_session() as session:
                    record = await session.get(AutoLoopTask, task_id)
                    if not self._owns_worker(task_id, worker):
                        return
                    if record and record.status not in {
                        TaskStatus.PAUSED.value,
                        TaskStatus.CANCELLED.value,
                    }:
                        record.status = TaskStatus.CANCELLED.value
                        record.interruption_reason = "cancelled"
                        record.finished_at = datetime.now(UTC)
                        await session.commit()
                current = record.status if record else TaskStatus.CANCELLED.value
                await self._emit_progress(task_id, {"status": current})

            except Exception as exc:
                error = f"Task execution failed ({type(exc).__name__}); manual review required before resubmission"
                logger.error("task_failed", task_id=task_id, error=error)
                await self._retry_or_fail(
                    task_id,
                    task_type,
                    owner_id,
                    payload,
                    handler,
                    error,
                    exc,
                    on_progress=_progress_cb,
                    worker=worker,
                    resolve_credentials=resolve_credentials,
                )

    async def _retry_or_fail(
        self,
        task_id: str,
        task_type: str,
        owner_id: str,
        payload: dict[str, Any],
        handler: Callable[..., Coroutine[Any, Any, Any]],
        error: str,
        exc: Exception,
        *,
        on_progress: Callable[..., Coroutine[Any, Any, Any]] | None = None,
        worker: asyncio.Task[Any] | None = None,
        resolve_credentials: bool = False,
    ) -> None:
        """Retry a failed task run before marking it failed.

        Transient model/tool failures are the common case (a user asked for
        retries explicitly), so a run gets ``max_task_retries`` re-executions;
        each one is announced on the progress stream as ``task_retry`` so the
        frontend can show that the task is retrying rather than dead. Once the
        budget is spent the task is recorded as failed for manual review.
        """
        if on_progress is None:

            async def on_progress(step: int, total: int, message: str = "") -> None:
                await self._persist_progress(task_id, step, total, message, worker=worker)

        attempts = 0
        last_error = error
        # Factory already retries read-only steps locally. Replaying the whole
        # handler can duplicate completed writes or an unconfirmed side effect.
        while task_type != "factory_run" and attempts < self._max_task_retries:
            attempts += 1
            async with async_session() as session:
                record = await session.get(AutoLoopTask, task_id)
                if (
                    self._owns_worker(task_id, worker)
                    and record
                    and record.status in {TaskStatus.RUNNING.value, TaskStatus.RETRYING.value}
                ):
                    record.status = TaskStatus.RETRYING.value
                    record.retry_count = (record.retry_count or 0) + 1
                    record.updated_at = datetime.now(UTC)
                    await session.commit()
                else:
                    return
            await self._emit_progress(
                task_id,
                {
                    "type": "task_retry",
                    "attempt": attempts,
                    "max_retries": self._max_task_retries,
                    "error": last_error,
                },
            )
            try:
                runtime_payload = payload
                if resolve_credentials and task_type in {"agent_run", "factory_run"}:
                    runtime_payload = await resolve_owner_agent_payload(owner_id, payload)
                runtime_payload = {**runtime_payload, "user_id": owner_id, "_task_id": task_id}
                if not self._owns_worker(task_id, worker):
                    return
                result = await handler(payload=runtime_payload, on_progress=on_progress)
                result_status = (
                    TaskStatus.FAILED.value
                    if isinstance(result, dict) and result.get("status") == TaskStatus.FAILED.value
                    else TaskStatus.COMPLETED.value
                )
                async with async_session() as session:
                    record = await session.get(AutoLoopTask, task_id)
                    if (
                        self._owns_worker(task_id, worker)
                        and record
                        and record.status == TaskStatus.RETRYING.value
                    ):
                        record.status = result_status
                        record.result = (
                            result if isinstance(result, dict) else {"output": str(result)}
                        )
                        record.error = (
                            str(result.get("error", ""))[:500]
                            if result_status == "failed"
                            else None
                        )
                        record.finished_at = datetime.now(UTC)
                        await session.commit()
                    else:
                        return
                await self._emit_progress(task_id, {"status": result_status, "result": result})
                return
            except Exception as retry_exc:
                last_error = (
                    f"Retry {attempts}/{self._max_task_retries} failed ({type(retry_exc).__name__})"
                )
                logger.warning(
                    "task_retry_failed",
                    task_id=task_id,
                    attempt=attempts,
                    error=last_error,
                )

        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if (
                self._owns_worker(task_id, worker)
                and record
                and record.status in {TaskStatus.RUNNING.value, TaskStatus.RETRYING.value}
            ):
                record.status = TaskStatus.FAILED.value
                record.error = last_error
                record.finished_at = datetime.now(UTC)
                await session.commit()
            else:
                return
        await self._emit_progress(task_id, {"status": "failed", "error": last_error})

    async def _persist_progress(
        self,
        task_id: str,
        step: int,
        total: int,
        message: str = "",
        *,
        worker: asyncio.Task[Any] | None = None,
    ) -> None:
        evaluation = {
            "percent": round((step / total) * 100, 2) if total else 0,
            "message": message,
            "step": step,
            "total": total,
        }
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if not self._owns_worker(task_id, worker):
                raise asyncio.CancelledError
            if record:
                if record.status in {TaskStatus.PAUSED.value, TaskStatus.CANCELLED.value}:
                    raise asyncio.CancelledError
                record.current_step = step
                record.max_steps = total
                record.heartbeat_at = datetime.now(UTC)
                record.progress_evaluation = evaluation
                record.checkpoint = {
                    **(record.checkpoint or {}),
                    "step": step,
                    "evaluation": evaluation,
                    "message": message,
                }
                await session.commit()
        await self._emit_progress(
            task_id, {"step": step, "total": total, **evaluation, "evaluation": evaluation}
        )

    async def _emit_progress(self, task_id: str, data: dict[str, Any]) -> None:
        await self.emit_event(task_id, "task_update", data)
        for cb in self._progress_callbacks:
            with suppress(Exception):
                await cb(task_id, data)


# Tools that leave durable traces (files, emails, money, remote state). A step
# whose payload requests any of them has already *acted* once it ran — rerunning
# the whole step would repeat the side effect (double-write, double-send), so
# task-level retries must never apply to it. Read-only steps stay retryable.
_SIDE_EFFECT_TOOLS = frozenset(
    {
        "write_file",
        "edit_file",
        "append_file",
        "file_delete",
        "run_command",
        "http_request",
        "web_search",
        "fetch",
        "post_message",
    }
)


def _step_has_side_effects(step_payload: dict[str, Any]) -> bool:
    """True when the step's tool list touches any durable-action tool."""
    tools = step_payload.get("tools") or []
    return any(str(tool) in _SIDE_EFFECT_TOOLS for tool in tools)


# Permission modes that map to the read-only tier in the existing permission
# evaluation chain (see TIER_MODES in app/api/v1/routes/reasoning.py).
_READ_ONLY_PERMISSION_MODES = frozenset({"plan", "strict"})


def _precheck_plan_steps(steps: list[dict[str, Any]], permission_mode: str) -> list[dict[str, Any]]:
    """Batch-precheck every planned step once, before execution starts.

    Moves the "intercept at run time" gate earlier: each step is checked for
    (a) tool names outside the factory tool whitelist and (b) side-effect tools
    under a read-only permission mode. Pure function — no IO, no payload — so
    plan dicts can be unit tested directly (sandbox review 5.2 item 3).
    """
    from app.core.permission_rules import normalize_tool_name

    known_tools = frozenset(
        normalized
        for tool_list in _FACTORY_SKILL_TOOLS.values()
        for tool in tool_list
        for normalized in (tool, normalize_tool_name(tool))
    )
    read_only = str(permission_mode).strip().lower() in _READ_ONLY_PERMISSION_MODES
    prechecks: list[dict[str, Any]] = []
    for position, step in enumerate(steps, start=1):
        index = int(step.get("step", position))
        tools = [str(tool) for tool in (step.get("tools") or [])]
        reasons: list[str] = [
            f"Unknown tool: {tool}"
            for tool in tools
            if normalize_tool_name(tool) not in known_tools
        ]
        if read_only:
            reasons.extend(
                f"Read-only permission mode blocks side-effect tool: {tool}"
                for tool in tools
                if str(tool) in _SIDE_EFFECT_TOOLS
            )
        prechecks.append(
            {
                "index": index,
                "tools": tools,
                "blocked": bool(reasons),
                "reasons": reasons,
            }
        )
    return prechecks


def _factory_permission_mode(payload: dict[str, Any]) -> str:
    """Resolve the permission mode governing this factory run.

    The factory call chain carries no agent session, so the mode is read from
    the caller's payload when present; otherwise the permissive auto default
    applies and the fallback is announced in the log.
    """
    from app.core.permission_rules import PermissionMode

    raw = str(payload.get("permission_mode", "") or "").strip()
    if raw:
        try:
            return PermissionMode(raw.lower()).value
        except ValueError:
            logger.warning(
                "factory_permission_mode_invalid",
                requested=raw,
                fallback=PermissionMode.AUTO.value,
            )
            return PermissionMode.AUTO.value
    logger.warning(
        "factory_permission_mode_missing",
        fallback=PermissionMode.AUTO.value,
    )
    return PermissionMode.AUTO.value


def _check_objective(objective: str) -> dict[str, Any]:
    """Validate the run's main goal before any model or tool call.

    A run whose goal cannot be pinned down is stopped here: executing with no
    main goal is exactly how a task drifts away from what the user asked for.
    needs_clarification keeps running — the caller's objective is authoritative
    — but the verdict is surfaced so downstream progress events can carry it.
    """
    from app.core.observability.alignment import validate_instruction_goal

    try:
        verdict = validate_instruction_goal(objective)
    except Exception as exc:
        logger.warning("objective_validation_failed", error=str(exc))
        return {"status": "ready", "goal_preserved": None, "plain_reason": None}
    if verdict.status == "blocked":
        return {
            "status": "blocked",
            "goal_preserved": False,
            "plain_reason": ("这个任务没有说清楚要达成什么目标，先补充目标再执行，避免跑偏。"),
        }
    return {"status": verdict.status, "goal_preserved": True, "plain_reason": None}


def _injected_system_prompt(payload: dict[str, Any]) -> str:
    """Prefer an explicit caller prompt, else inject the active core prompt.

    Callers that pass system_prompt are honoured unchanged (e.g. the factory
    planner speaks JSON only). Everyone else gets the versioned core prompt so
    a task never runs without the mandatory instructions.
    """
    explicit = str(payload.get("system_prompt", "")).strip()
    if explicit:
        return explicit
    try:
        from app.core.prompts import build_injected_prompt

        bundle = build_injected_prompt(
            task_type="implementation", model_id=str(payload.get("model", ""))
        )
        return str(bundle["system_prompt"])
    except Exception as exc:
        logger.warning("core_prompt_injection_failed", error=str(exc))
        return ""


async def handle_agent_run(
    payload: dict[str, Any], on_progress: Callable[[int, int, str], Awaitable[None]]
) -> dict[str, Any]:
    """Execute an autonomous agent run with the given objective."""
    from app.core.agent_engine import AgentEngine
    from app.core.di import resolve as di_resolve

    objective = payload.get("objective", "")
    if not objective.strip():
        raise ValueError("objective is required")

    goal_check = _check_objective(objective)
    if goal_check["status"] == "blocked":
        raise ValueError(goal_check["plain_reason"])

    max_steps = int(payload.get("max_steps", 10))
    try:
        engine: AgentEngine = di_resolve("AgentEngine")
    except KeyError:
        engine = AgentEngine()
    session = engine.create_session(
        agent_id="task-worker",
        user_id=str(payload.get("user_id", "system")),
        provider=str(payload.get("provider", "openai")),
        model_id=str(payload.get("model", "gpt-4o-mini")),
        api_key=str(payload.get("api_key", "")),
        base_url=payload.get("base_url"),
        system_prompt=_injected_system_prompt(payload),
        tools=payload.get("tools") or [],
    )
    session.max_iterations = max_steps
    output: list[str] = []
    current_iteration = 0
    completed = False
    async for event in engine.run(session, objective):
        if event.type.value == "thinking":
            current_iteration = int(event.data.get("iteration", current_iteration))
            await on_progress(
                current_iteration,
                max_steps,
                f"Running iteration {current_iteration}",
            )
        elif event.type.value == "text":
            output.append(str(event.data.get("content", "")))
        elif event.type.value == "error":
            raise RuntimeError("Agent execution failed")
        elif event.type.value == "done":
            if event.data.get("status") != "completed":
                raise RuntimeError("Agent ended without successful completion")
            completed = True
            current_iteration = int(event.data.get("iterations", current_iteration))
            if not output and event.data.get("content"):
                output.append(str(event.data["content"]))
    if not completed:
        raise RuntimeError("Agent stream ended without a completion event")
    await on_progress(current_iteration, max_steps, "Complete")
    return {
        "status": "completed",
        "output": "".join(output),
        "tokens_used": session.metrics.total_tokens_used,
        "iterations": session.metrics.total_iterations,
    }


def _build_factory_plan(goal: str, skills: list[str]) -> list[dict[str, Any]]:
    """Build a safe fallback plan from selected capabilities."""
    steps: list[dict[str, Any]] = []
    if "web_search" in skills:
        steps.append(
            {
                "action": "Research current evidence and constraints",
                "objective": f"Research reliable, current information needed to accomplish: {goal}",
                "tools": ["web_search"],
            }
        )
    if "file_manager" in skills or "code_reviewer" in skills:
        steps.append(
            {
                "action": "Inspect the existing project and identify the smallest correct change",
                "objective": f"Inspect the available project context and determine a concrete approach for: {goal}",
                "tools": ["read_file", "list_files"],
            }
        )
    execution_tools = [
        tool
        for skill in skills
        for tool in _FACTORY_SKILL_TOOLS.get(skill, [])
        if tool not in {"web_search", "read_file", "list_files"}
    ]
    steps.append(
        {
            "action": "Execute the goal and produce a verifiable result",
            "objective": goal,
            "tools": list(dict.fromkeys(execution_tools)),
        }
    )
    return [
        {"step": index, "status": "pending", **step} for index, step in enumerate(steps, start=1)
    ]


def _parse_factory_plan(raw_plan: str, goal: str, skills: list[str]) -> list[dict[str, Any]]:
    """Validate planner output and constrain it to selected tools."""
    text = raw_plan.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1])
    parsed = json.loads(text)
    raw_steps = parsed.get("steps") if isinstance(parsed, dict) else parsed
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("Planner returned no steps")
    allowed_tools = {tool for skill in skills for tool in _FACTORY_SKILL_TOOLS.get(skill, [])}
    plan: list[dict[str, Any]] = []
    for index, raw_step in enumerate(raw_steps[:5], start=1):
        if not isinstance(raw_step, dict):
            raise ValueError("Planner returned an invalid step")
        action = str(raw_step.get("action", "")).strip()
        objective = str(raw_step.get("objective", action)).strip()
        if not action or not objective:
            raise ValueError("Planner step is missing an action or objective")
        requested_tools = raw_step.get("tools", [])
        tools = (
            [str(tool) for tool in requested_tools if str(tool) in allowed_tools]
            if isinstance(requested_tools, list)
            else []
        )
        plan.append(
            {
                "step": index,
                "status": "pending",
                "action": action,
                "objective": objective,
                "tools": list(dict.fromkeys(tools)),
            }
        )
    return plan


_FACTORY_SKILL_TOOLS = {
    "code_executor": ["run_command"],
    "web_search": ["web_search"],
    "file_manager": ["read_file", "write_file", "list_files"],
    "data_analyzer": ["calculator"],
    "task_planner": [],
    "code_reviewer": ["read_file", "list_files"],
}


async def handle_factory_run(
    payload: dict[str, Any], on_progress: Callable[[int, int, str], Awaitable[None]]
) -> dict[str, Any]:
    """Run a planned multi-stage workflow; failed tool steps require manual review."""
    task_id = str(payload["_task_id"])
    goal = str(payload.get("objective", "")).strip()
    if not goal:
        raise ValueError("objective is required")

    goal_check = _check_objective(goal)
    if goal_check["status"] == "blocked":
        raise ValueError(goal_check["plain_reason"])

    skills = [str(skill) for skill in payload.get("factory_skills", [])]
    identity = {
        key: payload.get(key)
        for key in ("objective", "factory_skills", "tools", "permission_mode", "max_steps")
    }
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    checkpoint = payload.get("_factory_checkpoint")
    saved = None
    if checkpoint is not None:
        saved = checkpoint.get("factory") if isinstance(checkpoint, dict) else None
        if (
            not isinstance(saved, dict)
            or saved.get("version") != 1
            or saved.get("task_id") != task_id
            or saved.get("owner_id") != payload.get("user_id")
            or saved.get("fingerprint") != fingerprint
        ):
            raise ValueError("Invalid factory checkpoint; manual review required")
        plan = saved.get("plan")
        results: Any = saved.get("results")
        if (
            not isinstance(plan, list)
            or not plan
            or len(plan) > 5
            or not isinstance(results, list)
            or len(results) > len(plan)
            or any(
                not isinstance(step, dict)
                or step.get("step") != i
                or not isinstance(step.get("action"), str)
                or not step["action"]
                or not isinstance(step.get("objective"), str)
                or not step["objective"]
                or not isinstance(step.get("tools"), list)
                or any(not isinstance(tool, str) for tool in step["tools"])
                for i, step in enumerate(plan, 1)
            )
            or any(
                not isinstance(result, dict)
                or result.get("step") != i
                or result.get("action") != plan[i - 1]["action"]
                or not isinstance(result.get("output"), str)
                for i, result in enumerate(results, 1)
            )
        ):
            raise ValueError("Invalid factory step checkpoint; manual review required")
        if (
            saved.get("plan_digest")
            != hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
        ):
            raise ValueError("Mismatched factory plan; manual review required")
        if saved.get("recovery_blocked") or "[REDACTED]" in json.dumps(
            {"plan": plan, "results": results}
        ):
            raise ValueError(
                "Redacted factory execution content is not recoverable; manual review required"
            )
        active = saved.get("in_flight")
        if active is not None:
            if type(active) is not int or active != len(results) + 1 or active > len(plan):
                raise ValueError("Invalid factory active step; manual review required")
            tools = plan[active - 1]["tools"] or payload.get("tools", [])
            if _step_has_side_effects({"tools": tools}):
                raise ValueError("Unconfirmed factory side effect; manual review required")

    save_checkpoint = payload.get("_save_factory_checkpoint")

    async def save_boundary(in_flight: int | None) -> None:
        if save_checkpoint is not None:
            await save_checkpoint(
                {
                    "version": 1,
                    "task_id": task_id,
                    "owner_id": payload.get("user_id"),
                    "fingerprint": fingerprint,
                    "plan": plan,
                    "results": results,
                    "in_flight": in_flight,
                }
            )

    # Runtime controls and checkpoint data must never reach child model calls.
    payload = {
        key: value
        for key, value in payload.items()
        if key not in {"_factory_checkpoint", "_save_factory_checkpoint"}
    }
    await task_manager.emit_event(
        task_id,
        "factory_start",
        {"task_id": task_id, "goal_preserved": goal_check["goal_preserved"]},
    )
    await task_manager.emit_event(task_id, "planning", {"message": "Creating execution plan"})
    agent_handler = task_manager._handlers["agent_run"]
    planner_payload = {
        **payload,
        "objective": (
            "Create a concise execution plan for the goal below. Return JSON only as "
            '{"steps":[{"action":"...","objective":"...","tools":["..."]}]}. '
            f"Use at most 5 steps and only these tools: {payload.get('tools', [])}.\n\n"
            f"Goal: {goal}"
        ),
        "tools": [],
        "max_steps": 3,
    }
    planner_payload.pop("_task_id", None)
    try:
        planner_result = (
            await agent_handler(
                payload=planner_payload,
                on_progress=lambda *_: asyncio.sleep(0),
            )
            if saved is None
            else {"output": json.dumps({"steps": saved["plan"]})}
        )
        planner_output = (
            planner_result.get("output", "")
            if isinstance(planner_result, dict)
            else str(planner_result)
        )
        plan = _parse_factory_plan(planner_output, goal, skills) if saved is None else saved["plan"]
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        plan = _build_factory_plan(goal, skills)
        await task_manager.emit_event(task_id, "plan_fallback", {"reason": str(exc)})
    await task_manager.emit_event(
        task_id,
        "plan",
        {
            "steps": [
                {
                    "step": step["step"],
                    "action": step["action"],
                    "status": "pending",
                    **({"tool": step["tools"][0]} if step.get("tools") else {}),
                }
                for step in plan
            ]
        },
    )

    # Plan-stage batch precheck: unknown tools and side-effect tools under a
    # read-only permission mode are flagged once, up front, instead of being
    # caught one by one at execution time (sandbox review 5.2 item 3).
    permission_mode = _factory_permission_mode(payload)
    precheck_by_step = {
        precheck["index"]: precheck for precheck in _precheck_plan_steps(plan, permission_mode)
    }

    results = list(saved["results"]) if saved is not None else []
    await save_boundary(None)
    for index, step in enumerate(plan, start=1):
        if index <= len(results):
            continue
        step_id = f"{task_id}:{index}"
        precheck = precheck_by_step.get(index) or {"blocked": False, "reasons": []}
        if precheck["blocked"]:
            # A blocked step is recorded with the same step-failure structure as
            # an execution failure, but the run continues with the remaining steps.
            error = f"Step blocked by plan precheck ({'; '.join(precheck['reasons'])})"
            logger.warning(
                "factory_step_blocked",
                task_id=task_id,
                step=index,
                reasons=precheck["reasons"],
            )
            await task_manager.emit_event(
                task_id,
                "task_failed",
                {
                    "task_id": step_id,
                    "step": index,
                    "error": error,
                },
            )
            results.append({"step": index, "action": step["action"], "output": "", "blocked": True})
            await save_boundary(None)
            continue
        await task_manager.emit_event(
            task_id,
            "task_start",
            {
                "task_id": step_id,
                "step": index,
                "description": step["action"],
            },
        )
        step_payload = {
            **payload,
            "objective": step["objective"],
            "tools": step["tools"] or payload.get("tools", []),
            "max_steps": min(int(payload.get("max_steps", 10)), 6),
        }
        step_payload.pop("_task_id", None)

        async def _step_progress(
            current: int,
            total: int,
            message: str = "",
            _step_id: str = step_id,
            _index: int = index,
        ) -> None:
            await task_manager.emit_event(
                task_id,
                "progress",
                {
                    "task_id": _step_id,
                    "step": _index,
                    "current": current,
                    "total": total,
                    "message": message,
                },
            )

        # A failed step is retried before the run gives up: transient model/tool
        # errors are common, and each retry is announced so the UI can show the
        # step as retrying rather than silently dead. Steps whose tools have
        # durable side effects are exempt — the step already acted, so a retry
        # would repeat real-world actions (see review6 regression contract).
        _retryable = not _step_has_side_effects(step_payload)
        await save_boundary(index)
        last_error: Exception | None = None
        for attempt in range(1, task_manager.max_task_retries + 2):
            try:
                result = await agent_handler(payload=step_payload, on_progress=_step_progress)
                if isinstance(result, dict) and result.get("status") == TaskStatus.FAILED.value:
                    raise RuntimeError("Factory step reported failure")
                output = result.get("output", "") if isinstance(result, dict) else str(result)
                last_error = None
                break
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_error = exc
                if not _retryable:
                    # The step already acted on the world; rerunning it would
                    # repeat the side effect. Give up on this step immediately.
                    break
                if attempt <= task_manager.max_task_retries:
                    await task_manager.emit_event(
                        task_id,
                        "task_retry",
                        {
                            "task_id": step_id,
                            "step": index,
                            "retries": attempt,
                            "error": str(exc),
                        },
                    )
                    await asyncio.sleep(0.5)
                else:
                    break
        if last_error is not None:
            error = f"Step execution failed ({type(last_error).__name__})"
            await task_manager.emit_event(
                task_id,
                "task_failed",
                {
                    "task_id": step_id,
                    "step": index,
                    "error": error,
                },
            )
            raise RuntimeError(f"Factory step {index} failed: {error}") from None
        # Persistence failure must exit the handler, never re-execute the step.
        results.append({"step": index, "action": step["action"], "output": output})
        await save_boundary(None)
        await task_manager.emit_event(
            task_id,
            "task_complete",
            {
                "task_id": step_id,
                "step": index,
                "result": output,
            },
        )
        await on_progress(index, len(plan) + 1, step["action"])

    evidence = "\n\n".join(
        f"Step {item['step']} - {item['action']}:\n{item['output']}" for item in results
    )
    synthesis_payload = {
        **payload,
        "objective": (
            f"Produce the final answer for this goal:\n{goal}\n\n"
            f"Use these completed step results as evidence:\n{evidence}"
        ),
        "tools": [],
        "max_steps": 4,
    }
    synthesis_payload.pop("_task_id", None)
    try:
        synthesis = await agent_handler(
            payload=synthesis_payload, on_progress=lambda *_: asyncio.sleep(0)
        )
        report = synthesis.get("output", "") if isinstance(synthesis, dict) else str(synthesis)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("factory_synthesis_failed", task_id=task_id, error=str(exc))
        report = evidence
    await on_progress(len(plan) + 1, len(plan) + 1, "Synthesis complete")
    await task_manager.emit_event(task_id, "synthesize", {"report": report})
    return {"output": report, "plan": plan, "steps": results}


async def handle_data_processing(
    payload: dict[str, Any], on_progress: Callable[[int, int, str], Awaitable[None]]
) -> dict[str, Any]:
    """Process data: transform, filter, aggregate.

    Results beyond the default 100-row window stay reachable through the
    ``offset`` parameter, so large inputs are never silently dropped.
    """
    data = payload.get("data", [])
    operation = payload.get("operation", "identity")
    offset = max(0, int(payload.get("offset", 0)))
    limit = max(1, int(payload.get("limit", 100)))
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
            await on_progress(i + 1, total, f"Processed {i + 1}/{total}")
            await asyncio.sleep(0)
    await on_progress(total, total, "Complete")
    window = results[offset : offset + limit]
    next_offset = offset + len(window) if offset + len(window) < len(results) else None
    return {
        "processed": len(results),
        "results": window,
        "results_truncated": len(results) > offset + len(window),
        "results_returned": len(window),
        "results_total": len(results),
        "next_offset": next_offset,
    }


async def handle_workflow(
    payload: dict[str, Any], on_progress: Callable[[int, int, str], Awaitable[None]]
) -> dict[str, Any]:
    """Execute a multi-step workflow."""
    from app.multi_agent.flow import Flow

    workflow_name = payload.get("workflow", "default")
    params = payload.get("params", {})
    flow = Flow(name=workflow_name)
    return await flow.execute(params=params, on_progress=on_progress)


task_manager = TaskManager(max_workers=settings.max_concurrent_subtasks)
task_manager.register("agent_run", handle_agent_run)
task_manager.register("factory_run", handle_factory_run)
task_manager.register("data_processing", handle_data_processing)
task_manager.register("workflow", handle_workflow)


async def run_standalone_worker() -> None:
    """Poll never-started TaskManager rows; do not start AutoLoop recovery here."""
    logger.info("standalone_worker_started")
    while True:
        await task_manager.recover_pending_tasks()
        await asyncio.sleep(5)
