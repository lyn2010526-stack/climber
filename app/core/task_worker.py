"""Task worker — persistent async task execution with progress tracking.

Durability contract
-------------------
Every task is one row in ``auto_loop_tasks`` and the row is the single source of
truth for its lifecycle. Two rules make that survive a crash:

* **A running task is only ever touched by the worker that claimed it.** The
  claim is a conditional ``UPDATE ... WHERE id = ? AND status = 'pending'``, so
  a second worker, or a recovery sweep, can only win a row nobody owns
  (see :meth:`TaskManager._claim_attempt`).
* **Liveness is a timestamp, not a flag.** While a task executes, the worker
  refreshes ``heartbeat_at`` every ``_HEARTBEAT_INTERVAL`` seconds. A row whose
  newest liveness stamp is older than ``DEFAULT_STALE_RUNNING_AFTER`` is assumed
  to belong to a crashed process and becomes eligible for reclaim; a live
  worker can never be mistaken for one (see :func:`reclaim_stale_running_tasks`).

Failures are classified before they are acted on. A validation error is
permanent and fails the task once; a network blip is retryable and is retried
with exponential backoff plus jitter, up to ``max_attempts`` (see
:func:`classify_failure` and :class:`RetryPolicy`).
"""
from __future__ import annotations

import asyncio
import json
import random
import uuid
from collections import OrderedDict, defaultdict, deque
from collections.abc import Callable, Coroutine
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.storage import async_session
from app.storage.models_platform import AutoLoopTask

logger = structlog.get_logger()

# Keep the liveness loop independent from callers that instrument the retry
# sleep to observe backoff timings.
_sleep = asyncio.sleep

_SENSITIVE_PAYLOAD_KEYS = {"api_key", "api_key_encrypted"}

#: ``auto_loop_tasks.source`` discriminator written by this module. The other
#: writer of the table (``app/core/auto_loop.py``) uses ``AUTO_LOOP_SOURCE``;
#: each engine reclaims only its own rows.
TASK_WORKER_SOURCE = "task_worker"

#: How often a running task refreshes ``heartbeat_at``.
_HEARTBEAT_INTERVAL = 15.0

#: A RUNNING row whose newest liveness stamp is older than this many seconds is
#: treated as abandoned by a crashed worker. Comfortably larger than
#: ``_HEARTBEAT_INTERVAL`` so ordinary scheduling jitter never trips it.
DEFAULT_STALE_RUNNING_AFTER = 300.0


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FailureKind(StrEnum):
    """Whether a failure is worth spending another attempt on."""

    RETRYABLE = "retryable"
    PERMANENT = "permanent"


class RetryableTaskError(Exception):
    """Handler-raised marker forcing a retry whatever the classifier says.

    Use it when a provider hiccup surfaces as an application error whose type
    carries no signal (a bare ``RuntimeError`` from a model client, say).
    """


class PermanentTaskError(Exception):
    """Handler-raised marker forcing a permanent failure, attempt budget or not."""


def _http_status(exc: BaseException) -> int | None:
    """Best-effort HTTP status carried by a provider/HTTP client exception."""
    for attribute in ("status_code", "code"):
        value = getattr(exc, attribute, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


# Exception types that never become valid on a second attempt: a bad payload, a
# missing key, a refused permission. ``OSError`` is deliberately absent — its
# subclasses ``FileNotFoundError`` and ``PermissionError`` are listed, while
# ``ConnectionError``/``TimeoutError`` below are the transient ones.
_PERMANENT_ERROR_TYPES: tuple[type[BaseException], ...] = (
    AttributeError,
    FileNotFoundError,
    ImportError,
    IndexError,
    KeyError,
    NotImplementedError,
    PermissionError,
    TypeError,
    ValueError,
)
_RETRYABLE_ERROR_TYPES: tuple[type[BaseException], ...] = (
    ConnectionError,
    TimeoutError,
)
# 4xx other than the two codes below are the caller's fault; retrying them
# only repeats the rejection.
_RETRYABLE_HTTP_STATUS: frozenset[int] = frozenset({408, 425, 429})
_RETRYABLE_TEXT: tuple[str, ...] = (
    "temporarily unavailable",
    "temporary failure",
    "temporarily",
    "service unavailable",
    "rate limit",
    "too many requests",
    "timed out",
    "timeout",
    "connection reset",
    "connection aborted",
    "connection refused",
    "connection error",
    "remote end closed",
    "overloaded",
    "try again",
)
_PERMANENT_TEXT: tuple[str, ...] = (
    "is required",
    "not found",
    "no such",
    "unknown task type",
    "invalid",
    "validation",
    "unsupported",
    "forbidden",
    "unauthorized",
    "denied",
)


def classify_failure(exc: BaseException) -> FailureKind:
    """Decide whether a failed attempt is worth retrying.

    The default is :attr:`FailureKind.PERMANENT`. An unrecognised error in a
    system that bills per token must not burn a retry budget on a failure that
    will reproduce identically; handlers signal a genuine transient fault with
    :class:`RetryableTaskError` or a recognised transport/HTTP error.
    """
    if isinstance(exc, PermanentTaskError):
        return FailureKind.PERMANENT
    if isinstance(exc, RetryableTaskError):
        return FailureKind.RETRYABLE

    status = _http_status(exc)
    if status is not None:
        return (
            FailureKind.RETRYABLE
            if status >= 500 or status in _RETRYABLE_HTTP_STATUS
            else FailureKind.PERMANENT
        )
    if isinstance(exc, _PERMANENT_ERROR_TYPES):
        return FailureKind.PERMANENT
    if isinstance(exc, _RETRYABLE_ERROR_TYPES):
        return FailureKind.RETRYABLE
    return classify_failure_text(str(exc))


def classify_failure_text(message: str) -> FailureKind:
    """Classify a failure described only by its message.

    Handlers report their outcome as a ``{"status": "failed", "error": ...}``
    dict rather than by raising, so the same decision has to be available for
    text. Retryable markers win: a timeout inside a longer message must not be
    masked by an incidental "invalid" word.
    """
    lowered = (message or "").lower()
    if not lowered:
        return FailureKind.PERMANENT
    if any(marker in lowered for marker in _RETRYABLE_TEXT):
        return FailureKind.RETRYABLE
    if any(marker in lowered for marker in _PERMANENT_TEXT):
        return FailureKind.PERMANENT
    return FailureKind.PERMANENT


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded retry with exponential backoff and jitter.

    ``delay_for(attempt)`` is the wait *after* the 1-based ``attempt`` failed,
    so the first retry waits around ``base_delay`` and each later one doubles
    up to ``max_delay``. Jitter is proportional (± ``jitter_ratio``) so a fleet
    of workers that failed together does not retry together.
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter_ratio: float = 0.5

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay < 0 or self.max_delay < 0:
            raise ValueError("delays must be >= 0")
        if not 0.0 <= self.jitter_ratio <= 1.0:
            raise ValueError("jitter_ratio must be within [0, 1]")

    def delay_for(self, attempt: int) -> float:
        """Return the jittered backoff to wait after ``attempt`` failed."""
        if attempt < 1:
            return 0.0
        ceiling = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
        spread = ceiling * self.jitter_ratio
        return max(0.0, ceiling + random.uniform(-spread, spread))


DEFAULT_RETRY_POLICY = RetryPolicy()

#: SQL expression for "when did this row last show a sign of life?". The first
#: non-null stamp wins, so a task that crashed before its first heartbeat still
#: ages out via ``updated_at``/``started_at``/``created_at`` instead of
#: looking infinitely fresh.
_liveness_stamp = func.coalesce(
    AutoLoopTask.heartbeat_at,
    AutoLoopTask.updated_at,
    AutoLoopTask.started_at,
    AutoLoopTask.created_at,
)

#: Columns revision ``e6f7a8b9c0d1`` adds, with the SQL definition used when the
#: table has to be patched in place. ``app/storage/__init__.py::init_db`` builds
#: tables with ``Base.metadata.create_all``, which never adds a column to a
#: table that already exists, so a database created that way — and never brought
#: under alembic — would fail every task write with "no column named attempts".
#: This mirrors ``app/storage/database.py::ensure_checkpoint_schema``, which
#: solves the same problem for ``checkpoints``. Alembic remains the real answer;
#: this is the safety net so a task write never fails on a schema gap.
_TASK_COLUMNS: tuple[tuple[str, str], ...] = (
    ("attempts", "INTEGER NOT NULL DEFAULT 0"),
    ("max_attempts", "INTEGER NOT NULL DEFAULT 3"),
    ("last_error", "TEXT"),
    ("idempotency_key", "VARCHAR(128)"),
    ("source", "VARCHAR(20) NOT NULL DEFAULT 'auto_loop'"),
)
_TASK_IDEMPOTENCY_INDEX = "ix_auto_loop_tasks_idempotency_key"
_task_schema_ready = False



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


@dataclass
class _AttemptOutcome:
    """Normalised result of one attempt, success or failure."""

    status: str
    result: Any = None
    error: str = ""
    failure_kind: FailureKind | None = None
    cause: BaseException | None = None

    @property
    def ok(self) -> bool:
        return self.failure_kind is None


@dataclass
class RecoveryReport:
    """What a recovery sweep reclaimed and restarted."""

    reclaimed: list[str] = None  # type: ignore[assignment]
    enqueued: list[str] = None  # type: ignore[assignment]
    skipped: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.reclaimed = []
        self.enqueued = []
        self.skipped = []

    def __len__(self) -> int:
        return len(self.enqueued)


class TaskManager:
    """Manages task lifecycle: submit, execute, track, cancel.

    Args:
        max_workers: concurrent executions allowed by the internal semaphore.
        retry_policy: attempt budget and backoff curve applied to retryable
            failures. Per-task ``max_attempts`` overrides only the budget.
        heartbeat_interval: seconds between ``heartbeat_at`` refreshes while a
            task runs. Must stay well below
            ``DEFAULT_STALE_RUNNING_AFTER`` so a live task is never reclaimed.
    """

    def __init__(
        self,
        max_workers: int = 3,
        *,
        retry_policy: RetryPolicy | None = None,
        heartbeat_interval: float = _HEARTBEAT_INTERVAL,
    ):
        self._handlers: dict[str, Callable[..., Coroutine]] = {}
        self._semaphore = asyncio.Semaphore(max_workers)
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._progress_callbacks: list[Callable[[str, dict], Coroutine]] = []
        self._event_history: OrderedDict[str, deque[dict[str, Any]]] = OrderedDict()
        self._event_subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._retry_policy = retry_policy or DEFAULT_RETRY_POLICY
        self._heartbeat_interval = heartbeat_interval

    async def ensure_schema(self) -> None:
        """Idempotently add the retry/recovery columns if they are missing.

        Only needed for a database whose ``auto_loop_tasks`` table was created
        by ``Base.metadata.create_all`` before those columns existed;
        ``create_all`` skips existing tables, so it cannot add them and
        ``alembic upgrade`` is the proper fix. Runs at most once per process.
        """
        global _task_schema_ready
        if _task_schema_ready:
            return
        from sqlalchemy import inspect, text

        from app.storage import engine

        if engine.dialect.name != "sqlite":
            _task_schema_ready = True
            return
        try:
            async with engine.begin() as connection:
                def _missing(sync_connection: Any) -> list[tuple[str, str]]:
                    inspector = inspect(sync_connection)
                    if not inspector.has_table(AutoLoopTask.__tablename__):
                        return []
                    present = {
                        column["name"]
                        for column in inspector.get_columns(AutoLoopTask.__tablename__)
                    }
                    return [entry for entry in _TASK_COLUMNS if entry[0] not in present]

                for name, definition in await connection.run_sync(_missing):
                    await connection.execute(
                        text(f'ALTER TABLE "{AutoLoopTask.__tablename__}" ADD COLUMN "{name}" {definition}')
                    )
                has_index = await connection.run_sync(
                    lambda sync_connection: any(
                        index["name"] == _TASK_IDEMPOTENCY_INDEX
                        for index in inspect(sync_connection).get_indexes(AutoLoopTask.__tablename__)
                    )
                )
                if not has_index:
                    await connection.execute(
                        text(
                            f'CREATE UNIQUE INDEX "{_TASK_IDEMPOTENCY_INDEX}" '
                            f'ON "{AutoLoopTask.__tablename__}" (idempotency_key)'
                        )
                    )
            logger.info("task_schema_columns_ensured")
        except Exception as exc:
            # Never block a task write on a best-effort schema patch: report it
            # and let the actual statement fail with the real error.
            logger.warning("task_schema_ensure_failed", error=str(exc))
        _task_schema_ready = True

    def register(self, task_type: str, handler: Callable[..., Coroutine]) -> None:
        self._handlers[task_type] = handler

    def on_progress(self, callback: Callable[[str, dict], Coroutine]) -> None:
        self._progress_callbacks.append(callback)

    def subscribe(self, task_id: str) -> asyncio.Queue[dict[str, Any]]:
        """Subscribe to task-specific lifecycle events, replaying recent history."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        for event in self._event_history.get(task_id, ()):
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

    async def emit_event(self, task_id: str, event_type: str, data: dict[str, Any]) -> None:
        event = {"type": event_type, "data": data}
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

    async def submit(
        self,
        task_type: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        max_attempts: int | None = None,
    ) -> str:
        """Persist a task and start it, returning its id.

        ``idempotency_key`` makes a repeated submission free: the second call
        returns the id of the row the first call created and starts no second
        execution, so a client that retries a POST after a lost response cannot
        be charged twice. The key stays bound to the row for the life of the
        task, so a duplicate that arrives after completion returns the finished
        task rather than re-running it.
        """
        if task_type not in self._handlers:
            raise ValueError(f"Unknown task type: {task_type}")

        await self.ensure_schema()

        if idempotency_key is not None:
            existing = await self._find_by_idempotency_key(idempotency_key)
            if existing is not None:
                logger.info(
                    "task_submit_deduplicated",
                    task_id=existing,
                    idempotency_key=idempotency_key,
                )
                return existing

        task_id = str(uuid.uuid4())[:12]
        now = datetime.now(UTC)
        budget = max(1, int(max_attempts or self._retry_policy.max_attempts))

        async with async_session() as session:
            persisted_payload = {
                key: value
                for key, value in payload.items()
                if key not in _SENSITIVE_PAYLOAD_KEYS
            }
            record = AutoLoopTask(
                id=task_id,
                objective=json.dumps({"type": task_type, **persisted_payload}),
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
                attempts=0,
                max_attempts=budget,
                last_error=None,
                idempotency_key=idempotency_key,
                source=TASK_WORKER_SOURCE,
            )
            session.add(record)
            try:
                await session.commit()
            except IntegrityError:
                # A concurrent submission with the same key won the race
                # between our lookup and this insert. Its row is the
                # authoritative one; adopt it instead of failing the request.
                await session.rollback()
                if idempotency_key is None:
                    raise
                existing = await self._find_by_idempotency_key(idempotency_key)
                if existing is None:
                    raise
                logger.info(
                    "task_submit_race_deduplicated",
                    task_id=existing,
                    idempotency_key=idempotency_key,
                )
                return existing

        return self._spawn(task_id, task_type, payload, max_attempts=budget)

    def _spawn(
        self,
        task_id: str,
        task_type: str,
        payload: dict[str, Any],
        *,
        max_attempts: int | None = None,
    ) -> str:
        """Start the in-process coroutine that drives an existing row.

        Used by :meth:`submit` and by :func:`recover_pending_tasks` so both
        paths execute a task through the same claim-and-retry loop, and only
        once per id.
        """
        worker = asyncio.create_task(
            self._run_task(task_id, task_type, payload, max_attempts=max_attempts)
        )
        self._active_tasks[task_id] = worker
        worker.add_done_callback(lambda _task: self._active_tasks.pop(task_id, None))
        return task_id

    async def _find_by_idempotency_key(self, idempotency_key: str) -> str | None:
        """Return the id of the task already carrying ``idempotency_key``."""
        async with async_session() as session:
            result = await session.execute(
                select(AutoLoopTask.id).where(
                    AutoLoopTask.idempotency_key == idempotency_key
                )
            )
            return result.scalar_one_or_none()

    async def cancel(self, task_id: str) -> bool:
        task = self._active_tasks.get(task_id)
        if task is None or task.done() or task.cancelling():
            return False
        task.cancel()
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if record:
                record.status = TaskStatus.CANCELLED.value
                record.finished_at = datetime.now(UTC)
                await session.commit()
        return True

    async def get_status(self, task_id: str) -> dict[str, Any] | None:
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if not record:
                return None
            status = self._describe_status(record)
            status.update({
                "task_id": record.id,
                "objective": self._objective_from_record(record.objective),
                "progress": record.current_step,
                "total_steps": record.max_steps,
                "result": record.result,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "started_at": record.started_at.isoformat() if record.started_at else None,
                "finished_at": record.finished_at.isoformat() if record.finished_at else None,
            })
            return status

    @staticmethod
    def _describe_status(record: AutoLoopTask) -> dict[str, Any]:
        """Retry-relevant view of a record, shared by every read path.

        ``error`` is the operator-facing summary (it names the attempt count and
        whether the failure was retryable), ``last_error`` the raw text of the
        newest failure. ``retryable`` is reported for terminal failures only:
        a task still being retried is not a failure yet.
        """
        error = record.error
        retryable: bool | None = None
        if error:
            retryable = f"{FailureKind.RETRYABLE.value} failure" in error
        return {
            "status": record.status,
            "error": error,
            "last_error": record.last_error,
            "attempts": record.attempts or 0,
            "max_attempts": record.max_attempts or 0,
            "retryable": retryable,
        }

    @staticmethod
    def _objective_from_record(raw_objective: str) -> str:
        try:
            payload = json.loads(raw_objective)
        except (TypeError, json.JSONDecodeError):
            return raw_objective
        return str(
            payload.get("objective")
            or payload.get("workflow")
            or payload.get("type")
            or ""
        )

    async def list_tasks(self, status_filter: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        async with async_session() as session:
            stmt = select(AutoLoopTask).order_by(AutoLoopTask.created_at.desc()).limit(limit)
            if status_filter:
                stmt = stmt.where(AutoLoopTask.status == status_filter)
            result = await session.execute(stmt)
            records = result.scalars().all()
            return [
                {
                    "task_id": r.id,
                    "objective": self._objective_from_record(r.objective)[:100],
                    "status": r.status,
                    "progress": r.current_step,
                    "total_steps": r.max_steps,
                    "attempts": r.attempts or 0,
                    "max_attempts": r.max_attempts or 0,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]

    async def _run_task(
        self,
        task_id: str,
        task_type: str,
        payload: dict[str, Any],
        *,
        max_attempts: int | None = None,
    ) -> None:
        """Execute a task, retrying retryable failures with backoff.

        Each pass through the loop spends one attempt: the row is claimed with
        a conditional UPDATE, the handler runs under a heartbeat, and the
        outcome decides whether to sleep and try again or write a terminal
        status. The row stays RUNNING across the backoff sleep so no recovery
        sweep can start a second execution of the same task, and the heartbeat
        keeps running so a crash during the sleep is still reclaimable.
        """
        async with self._semaphore:
            handler = self._handlers[task_type]
            policy = self._retry_policy
            budget = max(1, int(max_attempts or policy.max_attempts))
            heartbeat: asyncio.Task | None = None
            try:
                async with async_session() as session:
                    persisted = await session.get(AutoLoopTask, task_id)
                    starting_attempt = (persisted.attempts or 0) + 1 if persisted else 1
                for attempt in range(starting_attempt, budget + 1):
                    # Ownership is acquired once, on the first attempt. Later
                    # attempts re-run the handler under the ownership already
                    # held: the row stays RUNNING across the backoff sleep, so
                    # re-claiming it would fail its own PENDING predicate and
                    # any recovery sweep still cannot start a second run.
                    if not await self._claim_attempt(
                        task_id,
                        attempt=attempt,
                        initial_attempt=attempt == starting_attempt,
                    ):
                        # Someone else owns the row, or it was cancelled while
                        # queued. Executing it would double-charge.
                        logger.info("task_claim_rejected", task_id=task_id)
                        return
                    if heartbeat is None:
                        heartbeat = asyncio.create_task(
                            self._heartbeat_loop(task_id),
                            name=f"task-heartbeat:{task_id}",
                        )
                    try:
                        outcome = await self._run_attempt(task_id, handler, payload)
                    except asyncio.CancelledError:
                        await self._mark_cancelled(task_id)
                        return

                    if outcome.ok:
                        await self._persist_terminal(task_id, outcome)
                        await self._emit_progress(
                            task_id, {"status": outcome.status, "result": outcome.result}
                        )
                        return

                    if outcome.failure_kind is FailureKind.RETRYABLE and attempt < budget:
                        delay = policy.delay_for(attempt)
                        await self._persist_retry(task_id, outcome, attempt, budget, delay)
                        await self._emit_progress(task_id, {
                            "status": "retrying",
                            "attempt": attempt,
                            "max_attempts": budget,
                            "retry_in_seconds": delay,
                            "error": outcome.error,
                        })
                        await asyncio.sleep(delay)
                        continue

                    await self._persist_terminal(
                        task_id, outcome, attempt=attempt, max_attempts=budget
                    )
                    await self._emit_progress(
                        task_id,
                        {
                            "status": outcome.status,
                            "error": outcome.error,
                            "attempts": attempt,
                            "max_attempts": budget,
                            "retryable": outcome.failure_kind is FailureKind.RETRYABLE,
                        },
                    )
                    return
            finally:
                if heartbeat is not None:
                    heartbeat.cancel()
                    with suppress(asyncio.CancelledError):
                        await heartbeat

    async def _claim_attempt(
        self,
        task_id: str,
        *,
        attempt: int = 1,
        initial_attempt: bool = False,
    ) -> bool:
        """Move a PENDING row into RUNNING and count the first attempt.

        This is the optimistic lock that keeps a task single-owner. The status
        predicate is part of the UPDATE, so a row already claimed (by a live
        worker or by a concurrent recovery sweep) is never re-claimed, and
        ``attempts < max_attempts`` stops a task whose budget is gone from
        being picked up again. ``started_at`` keeps its first value so the
        original submission time survives retries.
        """
        now = datetime.now(UTC)
        expected_status = (
            TaskStatus.PENDING.value if initial_attempt else TaskStatus.RUNNING.value
        )
        expected_attempts = attempt - 1
        async with async_session() as session:
            result = await session.execute(
                update(AutoLoopTask)
                .where(
                    AutoLoopTask.id == task_id,
                    AutoLoopTask.status == expected_status,
                    AutoLoopTask.attempts == expected_attempts,
                    AutoLoopTask.attempts < AutoLoopTask.max_attempts,
                )
                .values(
                    status=TaskStatus.RUNNING.value,
                    started_at=func.coalesce(AutoLoopTask.started_at, now),
                    heartbeat_at=now,
                    updated_at=now,
                    attempts=AutoLoopTask.attempts + 1,
                )
                .execution_options(synchronize_session=False)
            )
            await session.commit()
            return result.rowcount == 1

    async def _heartbeat_loop(self, task_id: str) -> None:
        """Keep ``heartbeat_at`` fresh for as long as the task is RUNNING.

        The ``status == 'running'`` predicate is what makes this safe: a task
        that was cancelled or written to a terminal state stops being refreshed,
        so a heartbeat can never resurrect it. Errors are logged and the loop
        exits, because a heartbeat that cannot be written means the recovery
        sweep's liveness signal is broken and staying silent would only delay
        the diagnosis.
        """
        try:
            while True:
                await _sleep(self._heartbeat_interval)
                now = datetime.now(UTC)
                async with async_session() as session:
                    await session.execute(
                        update(AutoLoopTask)
                        .where(
                            AutoLoopTask.id == task_id,
                            AutoLoopTask.status == TaskStatus.RUNNING.value,
                        )
                        .values(heartbeat_at=now, updated_at=now)
                        .execution_options(synchronize_session=False)
                    )
                    await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("task_heartbeat_failed", task_id=task_id, error=str(exc))

    async def _run_attempt(
        self,
        task_id: str,
        handler: Callable[..., Coroutine],
        payload: dict[str, Any],
    ) -> _AttemptOutcome:
        """Run the handler once and normalise whatever it produced.

        Handlers signal failure either by raising or by returning
        ``{"status": "failed", "error": ...}``. Both are folded into a single
        :class:`_AttemptOutcome` with its retry decision already made, so
        ``_run_task`` has exactly one place where retry-versus-fail is decided.
        """
        async def _progress_cb(step: int, total: int, message: str = ""):
            async with async_session() as session:
                rec = await session.get(AutoLoopTask, task_id)
                if rec:
                    rec.current_step = step
                    rec.max_steps = total
                    rec.heartbeat_at = datetime.now(UTC)
                    await session.commit()
            await self._emit_progress(task_id, {"step": step, "total": total, "message": message})

        runtime_payload = {**payload, "_task_id": task_id}
        try:
            result = await handler(payload=runtime_payload, on_progress=_progress_cb)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            logger.warning(
                "task_attempt_raised",
                task_id=task_id,
                error=message,
                failure_kind=classify_failure(exc).value,
            )
            return _AttemptOutcome(
                status=TaskStatus.FAILED.value,
                error=message[:500],
                failure_kind=classify_failure(exc),
                cause=exc,
            )

        result_status = TaskStatus.COMPLETED.value
        handler_status = result.get("status") if isinstance(result, dict) else None
        if handler_status in {TaskStatus.FAILED.value, "error", "max_iterations_reached", "stopped", "cancelled"}:
            result_status = (
                TaskStatus.CANCELLED.value
                if handler_status == "stopped"
                else TaskStatus.FAILED.value
            )

        stored_result = result if isinstance(result, dict) else {"output": str(result)}
        if result_status == TaskStatus.COMPLETED.value:
            return _AttemptOutcome(status=result_status, result=stored_result)

        message = ""
        if isinstance(result, dict):
            message = str(result.get("error", "") or result.get("termination_reason") or "")
        return _AttemptOutcome(
            status=result_status,
            result=stored_result,
            error=message[:500],
            failure_kind=classify_failure_text(message) if result_status == TaskStatus.FAILED.value else None,
        )

    async def _persist_retry(
        self,
        task_id: str,
        outcome: _AttemptOutcome,
        attempt: int,
        max_attempts: int,
        delay: float,
    ) -> None:
        """Record a retryable failure that will be tried again.

        The status stays RUNNING on purpose: the task is owned by this worker
        for the whole backoff window, so no recovery sweep can start a second
        execution. Only the counters and the error move, which is what an
        operator needs to see a task flapping against a flaky provider.
        """
        now = datetime.now(UTC)
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if record is None:
                return
            record.last_error = outcome.error
            record.error = (
                f"{FailureKind.RETRYABLE.value} failure on attempt "
                f"{attempt}/{max_attempts}, retrying in {delay:.2f}s: {outcome.error}"
            )
            record.heartbeat_at = now
            record.updated_at = now
            await session.commit()
        logger.warning(
            "task_retry_scheduled",
            task_id=task_id,
            attempt=attempt,
            max_attempts=max_attempts,
            delay_seconds=delay,
            error=outcome.error,
        )

    async def _persist_terminal(
        self,
        task_id: str,
        outcome: _AttemptOutcome,
        *,
        attempt: int | None = None,
        max_attempts: int | None = None,
    ) -> None:
        """Write a terminal status, naming whether the failure was retryable."""
        now = datetime.now(UTC)
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if record is None:
                return
            record.status = outcome.status
            record.result = outcome.result
            record.finished_at = now
            record.heartbeat_at = None
            record.updated_at = now
            if outcome.status == TaskStatus.COMPLETED.value:
                record.error = None
                record.last_error = None
                record.current_step = record.max_steps
            else:
                record.last_error = outcome.error or None
                kind = outcome.failure_kind or FailureKind.PERMANENT
                spent = attempt if attempt is not None else (record.attempts or 0)
                cap = max_attempts if max_attempts is not None else (record.max_attempts or 0)
                record.error = (
                    f"{kind.value} failure after {spent}/{cap} attempt(s): "
                    f"{outcome.error or 'no detail reported'}"
                )
            await session.commit()
        log = logger.info if outcome.status == TaskStatus.COMPLETED.value else logger.error
        log(
            "task_terminal_status",
            task_id=task_id,
            status=outcome.status,
            attempts=attempt,
            max_attempts=max_attempts,
            failure_kind=outcome.failure_kind.value if outcome.failure_kind else None,
            error=outcome.error,
        )

    async def _mark_cancelled(self, task_id: str) -> None:
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if record is None:
                return
            record.status = TaskStatus.CANCELLED.value
            record.finished_at = datetime.now(UTC)
            record.heartbeat_at = None
            await session.commit()
        await self._emit_progress(task_id, {"status": "cancelled"})

    async def _emit_progress(self, task_id: str, data: dict) -> None:
        for cb in self._progress_callbacks:
            with suppress(Exception):
                await cb(task_id, data)


    async def reclaim_stale_running_tasks(
        self,
        *,
        stale_after: float = DEFAULT_STALE_RUNNING_AFTER,
        now: datetime | None = None,
    ) -> list[str]:
        """Return RUNNING rows abandoned by a crashed worker to PENDING.

        A row is *stale* when its newest liveness stamp — ``heartbeat_at``,
        falling back to ``updated_at``, ``started_at`` and finally
        ``created_at`` — is older than ``stale_after`` seconds. A live worker
        refreshes ``heartbeat_at`` every ``heartbeat_interval`` seconds, so a
        genuinely in-flight task always has a fresh stamp and is left alone.
        Nothing is reclaimed for being RUNNING; only for having stopped showing
        signs of life.

        The sweep is read-then-conditional-write, and the UPDATE repeats the
        liveness predicate. If a heartbeat lands between the two statements the
        row no longer matches, and the re-read then excludes it, so the ids
        returned are exactly the ones this sweep won.

        A crashed row that has already spent its whole budget is not re-queued:
        it is closed out as ``failed`` with the reason, because a PENDING row
        with no attempts left would look queued forever while nothing can ever
        claim it.

        Returns the ids moved back to PENDING.
        """
        now = now or datetime.now(UTC)
        cutoff = now - timedelta(seconds=max(0.0, stale_after))
        stale = (AutoLoopTask.status == TaskStatus.RUNNING.value, _liveness_stamp < cutoff)
        mine = AutoLoopTask.source == TASK_WORKER_SOURCE
        has_budget = AutoLoopTask.attempts < AutoLoopTask.max_attempts

        async with async_session() as session:
            candidates = (
                (
                    await session.execute(select(AutoLoopTask.id).where(*stale, mine))
                )
                .scalars()
                .all()
            )
            if not candidates:
                return []

            exhausted = (
                (
                    await session.execute(
                        select(AutoLoopTask.id).where(
                            AutoLoopTask.id.in_(candidates),
                            ~has_budget,
                        )
                    )
                )
                .scalars()
                .all()
            )
            if exhausted:
                await session.execute(
                    update(AutoLoopTask)
                    .where(
                        AutoLoopTask.id.in_(exhausted),
                        *stale,
                        mine,
                        ~has_budget,
                    )
                    .values(
                        status=TaskStatus.FAILED.value,
                        error=(
                            f"retryable failure; attempt budget of "
                            f"{AutoLoopTask.max_attempts} spent before the worker died"
                        ),
                        last_error="retry budget exhausted by a crashed worker",
                        finished_at=now,
                        heartbeat_at=None,
                        updated_at=now,
                    )
                    .execution_options(synchronize_session=False)
                )

            resumable = [task_id for task_id in candidates if task_id not in set(exhausted)]
            if resumable:
                await session.execute(
                    update(AutoLoopTask)
                    .where(*stale, mine, AutoLoopTask.id.in_(resumable))
                    .values(
                        status=TaskStatus.PENDING.value, heartbeat_at=None, updated_at=now
                    )
                    .execution_options(synchronize_session=False)
                )
            await session.commit()
            # Re-read rather than trusting the UPDATE's rowcount: this is the
            # set of rows that are PENDING *and* were stale candidates, i.e.
            # exactly the ones this sweep won the race for.
            reclaimed = (
                (
                    await session.execute(
                        select(AutoLoopTask.id).where(
                            AutoLoopTask.id.in_(resumable),
                            AutoLoopTask.status == TaskStatus.PENDING.value,
                        )
                    )
                )
                .scalars()
                .all()
            )

        if exhausted:
            logger.error(
                "crashed_task_retry_budget_spent",
                task_ids=list(exhausted),
            )
        if reclaimed:
            logger.warning(
                "stale_running_tasks_reclaimed",
                task_ids=list(reclaimed),
                stale_after=stale_after,
            )
        return list(reclaimed)

    async def recover_pending_tasks(
        self,
        *,
        stale_after: float = DEFAULT_STALE_RUNNING_AFTER,
        limit: int = 100,
        now: datetime | None = None,
    ) -> RecoveryReport:
        """Reclaim abandoned work and restart it, the crash-recovery entry point.

        Two steps, in this order: stale RUNNING rows go back to PENDING
        (:meth:`reclaim_stale_running_tasks`), then every PENDING row with
        budget left that this process is not already running is queued again.
        Rows resume under their original id, so the same row, the same
        ``idempotency_key`` and the same attempt count carry across the crash.

        Only rows this module wrote (``source == 'task_worker'``) are touched;
        ``app/core/auto_loop.py`` reclaims its own rows. A row whose task type is
        no longer registered is reported as skipped rather than failed, because
        a handler removed in a later deploy should not destroy its queued work.
        """
        await self.ensure_schema()
        report = RecoveryReport()
        report.reclaimed = await self.reclaim_stale_running_tasks(
            stale_after=stale_after, now=now
        )

        async with async_session() as session:
            rows = (
                (
                    await session.execute(
                        select(
                            AutoLoopTask.id, AutoLoopTask.objective, AutoLoopTask.max_attempts
                        )
                        .where(
                            AutoLoopTask.status == TaskStatus.PENDING.value,
                            AutoLoopTask.source == TASK_WORKER_SOURCE,
                            AutoLoopTask.attempts < AutoLoopTask.max_attempts,
                        )
                        .order_by(AutoLoopTask.created_at)
                        .limit(limit)
                    )
                )
                .all()
            )

        for task_id, objective, max_attempts in rows:
            if task_id in self._active_tasks:
                continue
            try:
                payload = json.loads(objective)
            except (TypeError, json.JSONDecodeError):
                report.skipped.append(task_id)
                logger.warning("task_recovery_unparsable_objective", task_id=task_id)
                continue
            task_type = str(payload.pop("type", "agent_run"))
            if task_type not in self._handlers:
                report.skipped.append(task_id)
                logger.warning(
                    "task_recovery_unknown_type", task_id=task_id, task_type=task_type
                )
                continue
            self._spawn(task_id, task_type, payload, max_attempts=max_attempts or None)
            report.enqueued.append(task_id)

        if report.enqueued:
            logger.info(
                "pending_tasks_recovered",
                enqueued=len(report.enqueued),
                reclaimed=len(report.reclaimed),
                skipped=len(report.skipped),
            )
        return report


async def handle_agent_run(payload: dict[str, Any], on_progress) -> dict[str, Any]:
    """Execute an autonomous agent run with the given objective."""
    from app.core.agent_engine import AgentEngine
    from app.core.di import resolve as di_resolve
    objective = payload.get("objective", "")
    if not objective.strip():
        raise ValueError("objective is required")
    max_steps = int(payload.get("max_steps", 10))
    try:
        engine = di_resolve("AgentEngine")
    except KeyError:
        engine = AgentEngine()
    session = engine.create_session(
        agent_id="task-worker",
        user_id=str(payload.get("user_id", "system")),
        provider=str(payload.get("provider", "openai")),
        model_id=str(payload.get("model", "gpt-4o-mini")),
        api_key=str(payload.get("api_key", "")),
        base_url=payload.get("base_url"),
        system_prompt=str(payload.get("system_prompt", "")),
        tools=payload.get("tools") or [],
    )
    session.max_iterations = max_steps
    output: list[str] = []
    current_iteration = 0
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
            error = str(event.data.get("error", "Agent execution failed"))
            evidence = "".join(output)
            termination_reason = event.data.get("termination_reason", "error")
            return {
                "status": "stopped" if termination_reason == "stopped" else "failed",
                "termination_reason": termination_reason,
                "evidence": evidence,
                "output": evidence,
                "error": error,
                "tokens_used": session.metrics.total_tokens_used,
                "iterations": session.metrics.total_iterations,
            }
        elif event.type.value == "done":
            terminal_status = str(event.data.get("status", "completed"))
            if terminal_status != "completed":
                evidence = "".join(output)
                return {
                    "status": "failed" if terminal_status in {"max_iterations_reached", "error"} else terminal_status,
                    "termination_reason": event.data.get("termination_reason", terminal_status),
                    "evidence": evidence,
                    "output": evidence,
                    "error": terminal_status,
                    "tokens_used": session.metrics.total_tokens_used,
                    "iterations": session.metrics.total_iterations,
                }
    completed_steps = max(current_iteration, 1)
    await on_progress(completed_steps, completed_steps, "Complete")
    return {
        "status": "completed",
        "termination_reason": "completed",
        "evidence": "".join(output),
        "output": "".join(output),
        "tokens_used": session.metrics.total_tokens_used,
        "iterations": session.metrics.total_iterations,
    }


def _build_factory_plan(goal: str, skills: list[str]) -> list[dict[str, Any]]:
    """Build a safe fallback plan from selected capabilities.

    Research and inspection read different sources and can run concurrently;
    the execution step depends on every preceding step so it still sees their
    results. ``depends_on`` uses 1-based step numbers.
    """
    steps: list[dict[str, Any]] = []
    if "web_search" in skills:
        steps.append({
            "action": "Research current evidence and constraints",
            "objective": f"Research reliable, current information needed to accomplish: {goal}",
            "tools": ["web_search"],
            "depends_on": [],
        })
    if "file_manager" in skills or "code_reviewer" in skills:
        steps.append({
            "action": "Inspect the existing project and identify the smallest correct change",
            "objective": f"Inspect the available project context and determine a concrete approach for: {goal}",
            "tools": ["read_file", "list_files"],
            "depends_on": [],
        })
    execution_tools = [
        tool
        for skill in skills
        for tool in _FACTORY_SKILL_TOOLS.get(skill, [])
        if tool not in {"web_search", "read_file", "list_files"}
    ]
    steps.append({
        "action": "Execute the goal and produce a verifiable result",
        "objective": goal,
        "tools": list(dict.fromkeys(execution_tools)),
        "depends_on": list(range(1, len(steps) + 1)),
    })
    return [
        {"step": index, "status": "pending", **step}
        for index, step in enumerate(steps, start=1)
    ]


def _parse_factory_plan(raw_plan: str, goal: str, skills: list[str]) -> list[dict[str, Any]]:
    """Validate planner output and constrain it to selected tools.

    A step may declare ``depends_on`` (1-based step numbers) to run after those
    steps; independent steps are eligible to run concurrently. When the planner
    omits ``depends_on`` the steps keep the historical linear ordering.
    """
    text = raw_plan.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1])
    parsed = json.loads(text)
    raw_steps = parsed.get("steps") if isinstance(parsed, dict) else parsed
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("Planner returned no steps")
    allowed_tools = {
        tool for skill in skills for tool in _FACTORY_SKILL_TOOLS.get(skill, [])
    }
    plan: list[dict[str, Any]] = []
    for index, raw_step in enumerate(raw_steps[:5], start=1):
        if not isinstance(raw_step, dict):
            raise ValueError("Planner returned an invalid step")
        action = str(raw_step.get("action", "")).strip()
        objective = str(raw_step.get("objective", action)).strip()
        if not action or not objective:
            raise ValueError("Planner step is missing an action or objective")
        requested_tools = raw_step.get("tools", [])
        tools = [
            str(tool) for tool in requested_tools
            if str(tool) in allowed_tools
        ] if isinstance(requested_tools, list) else []
        plan.append({
            "step": index,
            "status": "pending",
            "action": action,
            "objective": objective,
            "tools": list(dict.fromkeys(tools)),
            "depends_on": _normalize_depends_on(raw_step.get("depends_on"), index, len(raw_steps[:5])),
        })
    return plan


def _normalize_depends_on(raw: Any, index: int, total: int) -> list[int]:
    """Return valid 1-based dependency numbers, defaulting to the prior step."""
    if not isinstance(raw, list):
        # No explicit dependency: keep the plan linear.
        return [index - 1] if index > 1 else []
    deps: list[int] = []
    for item in raw:
        try:
            dep = int(item)
        except (TypeError, ValueError):
            raise ValueError("Planner step has an invalid depends_on value") from None
        if dep < 1 or dep >= index or dep > total:
            raise ValueError(f"Planner step {index} depends on an out-of-range step")
        if dep not in deps:
            deps.append(dep)
    return deps


_FACTORY_SKILL_TOOLS = {
    "code_executor": ["run_command"],
    "web_search": ["web_search"],
    "file_manager": ["read_file", "write_file", "list_files"],
    "data_analyzer": ["calculator"],
    "task_planner": [],
    "code_reviewer": ["read_file", "list_files"],
}

# Upper bound on independent factory steps executed at the same time. Kept low
# so concurrent steps do not exhaust provider rate limits or the worker pool.
_FACTORY_MAX_PARALLEL = 3


async def handle_factory_run(payload: dict[str, Any], on_progress) -> dict[str, Any]:
    """Run a planned, retryable multi-stage Agent Factory workflow."""
    task_id = str(payload["_task_id"])
    goal = str(payload.get("objective", "")).strip()
    if not goal:
        raise ValueError("objective is required")
    skills = [str(skill) for skill in payload.get("factory_skills", [])]
    await task_manager.emit_event(task_id, "factory_start", {"task_id": task_id})
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
        planner_result = await agent_handler(
            payload=planner_payload,
            on_progress=lambda *_: asyncio.sleep(0),
        )
        planner_output = (
            planner_result.get("output", "")
            if isinstance(planner_result, dict)
            else str(planner_result)
        )
        plan = _parse_factory_plan(planner_output, goal, skills)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        plan = _build_factory_plan(goal, skills)
        await task_manager.emit_event(task_id, "plan_fallback", {"reason": str(exc)})
    await task_manager.emit_event(task_id, "plan", {
        "steps": [
            {
                "step": step["step"],
                "action": step["action"],
                "status": "pending",
                "depends_on": step.get("depends_on", []),
                **({"tool": step["tools"][0]} if step.get("tools") else {}),
            }
            for step in plan
        ]
    })

    results: list[dict[str, Any]] = []

    async def _run_factory_step(index: int, step: dict[str, Any]) -> str:
        step_id = f"{task_id}:{index}"
        step_payload = {
            **payload,
            "objective": step["objective"],
            "tools": step["tools"] or payload.get("tools", []),
            "max_steps": min(int(payload.get("max_steps", 10)), 6),
        }
        step_payload.pop("_task_id", None)
        last_error: Exception | None = None
        for attempt in range(1, 3):
            try:
                async def _step_progress(current: int, total: int, message: str = "", _step_id: str = step_id, _index: int = index) -> None:
                    await task_manager.emit_event(task_id, "progress", {
                        "task_id": _step_id,
                        "step": _index,
                        "current": current,
                        "total": total,
                        "message": message,
                    })

                result = await agent_handler(payload=step_payload, on_progress=_step_progress)
                if isinstance(result, dict) and result.get("status") in {
                    TaskStatus.FAILED.value,
                    "error",
                    "max_iterations_reached",
                    "stopped",
                    "cancelled",
                }:
                    raise RuntimeError(str(result.get("error") or result.get("termination_reason") or "Step failed"))
                output = result.get("output", "") if isinstance(result, dict) else str(result)
                await task_manager.emit_event(task_id, "task_complete", {
                    "task_id": step_id,
                    "step": index,
                    "result": output,
                })
                return output
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    await task_manager.emit_event(task_id, "task_retry", {
                        "task_id": step_id,
                        "step": index,
                        "retries": attempt,
                        "error": str(exc),
                    })
                    await asyncio.sleep(0.5)
        error = str(last_error or "Step failed")
        await task_manager.emit_event(task_id, "task_failed", {
            "task_id": step_id,
            "step": index,
            "error": error,
        })
        raise RuntimeError(f"Factory step {index} failed: {error}")

    # Dependency-aware scheduling: a step starts once all its ``depends_on``
    # steps have finished. Independent steps run concurrently up to
    # ``_FACTORY_MAX_PARALLEL``; evidence is reassembled in step order below.
    results_by_step: dict[int, dict[str, Any]] = {}
    completed: set[int] = set()
    running: dict[int, asyncio.Task[str]] = {}
    pending = {step["step"]: step for step in plan}
    try:
        while pending or running:
            for index in sorted(pending):
                if len(running) >= _FACTORY_MAX_PARALLEL:
                    break
                step = pending[index]
                if any(dep not in completed for dep in step.get("depends_on", [])):
                    continue
                pending.pop(index)
                await task_manager.emit_event(task_id, "task_start", {
                    "task_id": f"{task_id}:{index}",
                    "step": index,
                    "description": step["action"],
                })
                running[index] = asyncio.create_task(_run_factory_step(index, step))
            if not running:
                raise RuntimeError("Factory plan has unsatisfiable step dependencies")
            done, _ = await asyncio.wait(set(running.values()), return_when=asyncio.FIRST_COMPLETED)
            for index, task in list(running.items()):
                if task not in done:
                    continue
                output = task.result()
                del running[index]
                results_by_step[index] = {"step": index, "action": plan[index - 1]["action"], "output": output}
                completed.add(index)
                await on_progress(index, len(plan) + 1, plan[index - 1]["action"])
    except BaseException:
        for task in running.values():
            task.cancel()
        for task in running.values():
            with suppress(asyncio.CancelledError):
                await task
        raise

    results = [results_by_step[index] for index in sorted(results_by_step)]

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
        synthesis = await agent_handler(payload=synthesis_payload, on_progress=lambda *_: asyncio.sleep(0))
        report = synthesis.get("output", "") if isinstance(synthesis, dict) else str(synthesis)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("factory_synthesis_failed", task_id=task_id, error=str(exc))
        report = evidence
    await on_progress(len(plan) + 1, len(plan) + 1, "Synthesis complete")
    await task_manager.emit_event(task_id, "synthesize", {"report": report})
    return {"status": "completed", "output": report, "plan": plan, "steps": results}


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
task_manager.register("factory_run", handle_factory_run)
task_manager.register("data_processing", handle_data_processing)
task_manager.register("workflow", handle_workflow)




async def recover_pending_tasks(
    *,
    stale_after: float = DEFAULT_STALE_RUNNING_AFTER,
    limit: int = 100,
    manager: TaskManager | None = None,
) -> RecoveryReport:
    """Reclaim and restart abandoned work on the process-wide manager."""
    return await (manager or task_manager).recover_pending_tasks(
        stale_after=stale_after, limit=limit
    )


async def reclaim_stale_running_tasks(
    *,
    stale_after: float = DEFAULT_STALE_RUNNING_AFTER,
    manager: TaskManager | None = None,
) -> list[str]:
    """Return crashed RUNNING rows to PENDING on the process-wide manager."""
    return await (manager or task_manager).reclaim_stale_running_tasks(stale_after=stale_after)


async def run_standalone_worker(
    *,
    interval: float = 30.0,
    stale_after: float = DEFAULT_STALE_RUNNING_AFTER,
) -> None:
    """Poll for recoverable work until cancelled.

    Kept as the entry point for running the worker in a dedicated process; the
    in-process application reaches the same recovery through
    ``AutoLoopEngine.recover_interrupted_sessions`` at startup, which is the
    path that actually runs. It used to re-``submit`` recovered rows, minting a
    new id and a second row per pending task — a duplicate execution and a
    duplicate charge. It now only calls :func:`recover_pending_tasks`, so a task
    resumes under its own id and this loop holds no recovery logic of its own.
    """
    logger.info("standalone_worker_started", interval=interval, stale_after=stale_after)
    while True:
        try:
            await recover_pending_tasks(stale_after=stale_after)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("standalone_worker_sweep_failed", error=str(exc), exc_info=True)
        await asyncio.sleep(interval)
