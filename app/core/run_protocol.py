"""Unified Run protocol types and an in-memory persistence fake.

The in-memory store is intentionally small, but it enforces the invariants that
the SQLAlchemy implementation will share: conditional state transitions,
monotonic event sequences, idempotent event IDs, and execution fencing.
"""

from __future__ import annotations

import copy
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from app.core import AgentEventType, MessageRole


def _utc_now() -> datetime:
    return datetime.now(UTC)


class RunStatus(StrEnum):
    """Lifecycle states shared by all Run implementations."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


TERMINAL_RUN_STATUSES = frozenset(
    {
        RunStatus.COMPLETED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    }
)

ALLOWED_RUN_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.PENDING: frozenset(
        {
            RunStatus.RUNNING,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        }
    ),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.PAUSED,
        }
    ),
    RunStatus.PAUSED: frozenset(
        {
            RunStatus.RUNNING,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        }
    ),
    RunStatus.FAILED: frozenset({RunStatus.RUNNING}),
    RunStatus.COMPLETED: frozenset({RunStatus.RUNNING}),
    RunStatus.CANCELLED: frozenset({RunStatus.RUNNING}),
}

RUN_TRANSITION_FIELDS: frozenset[str] = frozenset(
    {
        "agent_id",
        "trace_id",
        "checkpoint_id",
        "error",
        "error_message",
        "metadata",
        "parent_run_id",
        "started_at",
        "completed_at",
    }
)

RUN_EVENT_VOCABULARY: frozenset[str] = frozenset(item.value for item in AgentEventType)

TERMINATION_REASON_USER_CANCEL = "cancelled_user"
TERMINATION_REASON_INTERRUPTED = "interrupted_by_recovery"
TERMINATION_REASON_ERROR = "error"


def is_known_run_event_type(event_type: str) -> bool:
    """Fail-closed vocabulary check for persisted Run events.

    Audit events are a reserved out-of-band family allowed beside the
    business vocabulary.
    """
    if event_type in RUN_EVENT_VOCABULARY:
        return True
    return event_type == "audit" or event_type.startswith("audit.")


def termination_metadata(reason: str, *, detail: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"reason": reason}
    if detail:
        payload["detail"] = detail
    return {"termination": payload}


def is_audit_event_type(event_type: str) -> bool:
    return event_type == "audit" or event_type.startswith("audit.")


def validate_execution_token(
    run_id: str,
    current_status: RunStatus,
    execution_token: int | None,
    current_execution_token: int,
) -> None:
    """Raise ``ExecutionTokenConflictError`` when the token is stale."""
    if execution_token is not None and execution_token != current_execution_token:
        raise ExecutionTokenConflictError(run_id, current_status, execution_token, current_execution_token)


def validate_run_transition(
    current: RunRecord,
    expected: RunStatus,
    target: RunStatus,
    execution_token: int | None,
) -> None:
    """Conditional transition guard: token + allowed state machine edge."""
    validate_execution_token(current.run_id, current.status, execution_token, current.execution_token)
    expected_status = RunStatus(expected)
    target_status = RunStatus(target)
    if current.status is not expected_status or target_status not in ALLOWED_RUN_TRANSITIONS[current.status]:
        raise RunStateConflictError(
            current.run_id,
            current.status,
            expected=expected_status,
            target=target_status,
        )


def validate_event_write(
    current: RunRecord,
    execution_token: int | None,
    event_type: str,
) -> None:
    """Execution token check + terminal Run rejects business events."""
    validate_execution_token(current.run_id, current.status, execution_token, current.execution_token)
    if current.is_terminal and not is_audit_event_type(event_type):
        raise RunStateConflictError(
            current.run_id,
            current.status,
            code="run_state_conflict",
            message=f"Run {current.run_id} is terminal and rejects business events",
        )


def merge_transition_metadata(
    current: RunRecord,
    supplied: dict[str, Any],
    target: RunStatus,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Merge metadata, apply RUNNING defaults and terminal defaults.

    Returns a dict of logical field values (not DB column names) suitable for
    ``replace(current, **returned)`` or custom column mapping.
    """
    supplied = dict(supplied)
    meta = copy.deepcopy(current.metadata)
    if "metadata" in supplied:
        meta.update(copy.deepcopy(supplied.pop("metadata") or {}))
    ref = now or _utc_now()
    result: dict[str, Any] = {"metadata": meta}
    for field_name, value in supplied.items():
        if field_name == "started_at":
            result["started_at"] = value
        elif field_name == "completed_at":
            result["completed_at"] = value
        elif field_name == "error":
            result["error"] = value
        elif field_name == "error_message":
            result["error_message"] = value
        elif field_name == "agent_id":
            result["agent_id"] = value
        elif field_name == "trace_id":
            result["trace_id"] = value
        elif field_name == "checkpoint_id":
            result["checkpoint_id"] = value
        elif field_name == "parent_run_id":
            result["parent_run_id"] = value
    if target is RunStatus.RUNNING:
        result.setdefault("started_at", current.started_at or ref)
        result.setdefault("completed_at", None)
        result.setdefault("error", None)
        result.setdefault("error_message", None)
    elif target in TERMINAL_RUN_STATUSES:
        result.setdefault("completed_at", ref)
    return result


class RunProtocolError(Exception):
    """Base error with a stable machine-readable code."""

    code = "run_protocol_error"

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": copy.deepcopy(self.details),
        }


class RunNotFoundError(RunProtocolError):
    code = "run_not_found"

    def __init__(self, run_id: str) -> None:
        super().__init__(f"Run {run_id} was not found", details={"run_id": run_id})
        self.run_id = run_id


class RunStateConflictError(RunProtocolError):
    """Raised when a conditional transition or event write is fenced."""

    code = "run_state_conflict"

    def __init__(
        self,
        run_id: str,
        current: RunStatus,
        *,
        expected: RunStatus | None = None,
        target: RunStatus | None = None,
        code: str | None = None,
        message: str | None = None,
    ) -> None:
        self.run_id = run_id
        self.current = RunStatus(current)
        self.expected = RunStatus(expected) if expected is not None else None
        self.target = RunStatus(target) if target is not None else None
        if code is not None:
            self.code = code
        details = {
            "run_id": run_id,
            "current": self.current.value,
            "expected": self.expected.value if self.expected is not None else None,
            "target": self.target.value if self.target is not None else None,
        }
        super().__init__(message or f"Run {run_id} cannot transition from {self.current.value}", details=details)


class ExecutionTokenConflictError(RunStateConflictError):
    """Raised when a stale worker attempts to write to a Run."""

    def __init__(self, run_id: str, current: RunStatus, expected_token: int, actual_token: int) -> None:
        self.expected_token = expected_token
        self.actual_token = actual_token
        super().__init__(
            run_id,
            current,
            code="execution_token_conflict",
            message=f"Execution token {expected_token} is stale for Run {run_id}",
        )
        self.details.update(
            {
                "expected_token": expected_token,
                "actual_token": actual_token,
            }
        )


class EventSequenceConflictError(RunStateConflictError):
    """Raised when an event would break the Run sequence."""

    def __init__(self, run_id: str, expected_sequence: int, actual_sequence: int) -> None:
        self.expected_sequence = expected_sequence
        self.actual_sequence = actual_sequence
        super().__init__(
            run_id,
            RunStatus.RUNNING,
            code="event_sequence_conflict",
            message=(
                f"Event sequence {actual_sequence} is invalid for Run {run_id}; "
                f"expected {expected_sequence}"
            ),
        )
        self.details.update(
            {
                "expected_sequence": expected_sequence,
                "actual_sequence": actual_sequence,
            }
        )


class CheckpointScopeMismatchError(RunProtocolError):
    code = "checkpoint_scope_mismatch"

    def __init__(self, run_id: str, checkpoint_id: str) -> None:
        super().__init__(
            f"Checkpoint {checkpoint_id} cannot be attached to Run {run_id}",
            details={"run_id": run_id, "checkpoint_id": checkpoint_id},
        )
        self.run_id = run_id
        self.checkpoint_id = checkpoint_id


class EventVocabularyError(RunProtocolError):
    """Raised when a persisted event type falls outside the Run vocabulary."""

    code = "event_vocabulary_invalid"

    def __init__(self, run_id: str, event_type: str) -> None:
        super().__init__(
            f"Event type {event_type} is not part of the Run event vocabulary",
            details={"run_id": run_id, "event_type": event_type},
        )
        self.run_id = run_id
        self.event_type = event_type


@dataclass(frozen=True, slots=True)
class RunRecord:
    """Persistent identity and lifecycle state for one Run."""

    run_id: str
    session_id: str
    user_id: str
    kind: str = "agent_chat"
    status: RunStatus = RunStatus.PENDING
    agent_id: str | None = None
    trace_id: str | None = None
    checkpoint_id: str | None = None
    last_sequence: int = 0
    execution_token: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: dict[str, Any] | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_run_id: str | None = None
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", RunStatus(self.status))
        object.__setattr__(self, "error", copy.deepcopy(self.error))
        object.__setattr__(self, "metadata", copy.deepcopy(self.metadata))

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_RUN_STATUSES

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "kind": self.kind,
            "status": self.status.value,
            "agent_id": self.agent_id,
            "trace_id": self.trace_id,
            "checkpoint_id": self.checkpoint_id,
            "last_sequence": self.last_sequence,
            "execution_token": self.execution_token,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": copy.deepcopy(self.error),
            "error_message": self.error_message,
            "metadata": copy.deepcopy(self.metadata),
            "parent_run_id": self.parent_run_id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class MessageEnvelope:
    """Stable message shape shared by providers, replay, and tracing."""

    message_id: str
    run_id: str
    session_id: str
    role: MessageRole
    content: Any
    created_at: datetime
    tool_call_id: str | None = None
    tool_name: str | None = None
    provider: str | None = None
    model_id: str | None = None
    raw_payload_ref: str | None = None
    raw_payload_summary: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", MessageRole(self.role))
        object.__setattr__(self, "content", copy.deepcopy(self.content))
        object.__setattr__(self, "raw_payload_summary", copy.deepcopy(self.raw_payload_summary))
        object.__setattr__(self, "metadata", copy.deepcopy(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "role": self.role.value,
            "content": copy.deepcopy(self.content),
            "created_at": self.created_at.isoformat(),
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "provider": self.provider,
            "model_id": self.model_id,
            "raw_payload_ref": self.raw_payload_ref,
            "raw_payload_summary": copy.deepcopy(self.raw_payload_summary),
            "metadata": copy.deepcopy(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> MessageEnvelope:
        created_at = payload["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        return cls(
            message_id=str(payload["message_id"]),
            run_id=str(payload["run_id"]),
            session_id=str(payload["session_id"]),
            role=MessageRole(payload["role"]),
            content=copy.deepcopy(payload.get("content")),
            created_at=created_at,
            tool_call_id=payload.get("tool_call_id"),
            tool_name=payload.get("tool_name"),
            provider=payload.get("provider"),
            model_id=payload.get("model_id"),
            raw_payload_ref=payload.get("raw_payload_ref"),
            raw_payload_summary=copy.deepcopy(payload.get("raw_payload_summary")),
            metadata=copy.deepcopy(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class RunEvent:
    """An ordered, replayable fact emitted by a Run."""

    event_id: str
    run_id: str
    sequence: int | None
    event_type: str
    data: dict[str, Any]
    created_at: datetime
    trace_id: str | None = None
    checkpoint_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", copy.deepcopy(self.data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "run_id": self.run_id,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "data": copy.deepcopy(self.data),
            "created_at": self.created_at.isoformat(),
            "trace_id": self.trace_id,
            "checkpoint_id": self.checkpoint_id,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RunEvent:
        created_at = payload["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        return cls(
            event_id=str(payload["event_id"]),
            run_id=str(payload["run_id"]),
            sequence=payload.get("sequence"),
            event_type=str(payload["event_type"]),
            data=copy.deepcopy(payload.get("data") or {}),
            created_at=created_at,
            trace_id=payload.get("trace_id"),
            checkpoint_id=payload.get("checkpoint_id"),
        )


@dataclass(frozen=True, slots=True)
class StartRun:
    """Input command for creating a Run."""

    session_id: str
    user_id: str
    agent_id: str | None = None
    kind: str = "agent_chat"
    trace_id: str | None = None
    message: MessageEnvelope | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResumeRun:
    """Input command for resuming a persisted Run."""

    run_id: str
    session_id: str
    user_id: str
    execution_token: int
    checkpoint_id: str | None = None


@dataclass(frozen=True, slots=True)
class RunHandle:
    """Opaque caller handle carrying the current fencing token."""

    run_id: str
    session_id: str
    execution_token: int
    status: RunStatus = RunStatus.RUNNING

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", RunStatus(self.status))


@dataclass(frozen=True, slots=True)
class ReplayPage:
    """A bounded replay response with enough metadata to detect gaps."""

    events: list[RunEvent]
    after: int
    oldest_sequence: int | None
    latest_sequence: int
    has_gap: bool = False
    has_more: bool = False
    next_after: int | None = None
    unknown_event_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "events", list(self.events))


@dataclass(frozen=True, slots=True)
class RunPage:
    """A bounded page of Runs with enough metadata for cursor pagination."""

    items: list[RunRecord]
    total: int
    limit: int
    offset: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", list(self.items))


RunState = RunRecord


class RunStore(Protocol):
    async def create(self, run: RunRecord) -> RunRecord: ...

    async def get(self, run_id: str) -> RunRecord | None: ...

    async def require(self, run_id: str) -> RunRecord: ...

    async def find_active_for_session(self, session_id: str) -> RunRecord | None: ...

    async def latest_run_for_session(self, session_id: str) -> RunRecord | None: ...

    async def list_runs(
        self,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        status: RunStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> RunPage: ...

    async def transition(
        self,
        run_id: str,
        expected: RunStatus,
        target: RunStatus,
        values: Mapping[str, Any] | None = None,
        execution_token: int | None = None,
    ) -> RunRecord: ...

    async def append_event(self, event: RunEvent, execution_token: int | None = None) -> RunEvent: ...

    async def list_events(self, run_id: str, after: int = 0, limit: int = 256) -> ReplayPage: ...

    async def attach_checkpoint(
        self,
        run_id: str,
        checkpoint_id: str,
        iteration: int,
        execution_token: int | None = None,
    ) -> None: ...


class RunRuntime(Protocol):
    async def start(self, command: StartRun) -> RunHandle: ...

    def stream(self, handle: RunHandle) -> AsyncIterator[RunEvent]: ...

    async def resume(self, command: ResumeRun) -> RunHandle: ...

    async def cancel(self, run_id: str, actor_id: str) -> RunState: ...

    async def replay(self, run_id: str, after: int = 0, limit: int = 256) -> ReplayPage: ...


class InMemoryRunStore:
    """Concurrency-safe fake used to prove Run invariants before DB wiring."""

    def __init__(self, event_capacity: int | None = None) -> None:
        if event_capacity is not None and event_capacity < 1:
            raise ValueError("event_capacity must be positive")
        self.event_capacity = event_capacity
        self._runs: dict[str, RunRecord] = {}
        self._events: dict[str, list[RunEvent]] = {}
        self._event_ids: dict[tuple[str, str], RunEvent] = {}
        import asyncio

        self._lock = asyncio.Lock()

    async def create(self, run: RunRecord) -> RunRecord:
        async with self._lock:
            if run.run_id in self._runs:
                current = self._runs[run.run_id]
                raise RunStateConflictError(
                    run.run_id,
                    current.status,
                    code="run_conflict",
                    message=f"Run {run.run_id} already exists",
                )
            stored = copy.deepcopy(run)
            if stored.status is RunStatus.RUNNING and stored.started_at is None:
                stored = replace(stored, started_at=_utc_now(), execution_token=max(stored.execution_token, 1))
            self._runs[stored.run_id] = stored
            self._events[stored.run_id] = []
            return copy.deepcopy(stored)

    async def get(self, run_id: str) -> RunRecord | None:
        async with self._lock:
            run = self._runs.get(run_id)
            return copy.deepcopy(run) if run is not None else None

    async def require(self, run_id: str) -> RunRecord:
        run = await self.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        return run

    async def transition(
        self,
        run_id: str,
        expected: RunStatus,
        target: RunStatus,
        values: Mapping[str, Any] | None = None,
        execution_token: int | None = None,
    ) -> RunRecord:
        expected_status = RunStatus(expected)
        target_status = RunStatus(target)
        async with self._lock:
            current = self._runs.get(run_id)
            if current is None:
                raise RunNotFoundError(run_id)
            validate_run_transition(current, expected_status, target_status, execution_token)

            supplied = dict(values or {})
            unknown = set(supplied) - RUN_TRANSITION_FIELDS
            if unknown:
                raise ValueError(f"Unsupported Run fields: {sorted(unknown)}")

            merged = merge_transition_metadata(current, supplied, target_status)
            next_token = (
                current.execution_token + 1
                if target_status is RunStatus.RUNNING
                else current.execution_token
            )
            updated = replace(
                current,
                status=target_status,
                execution_token=next_token,
                **merged,
            )
            self._runs[run_id] = updated
            return copy.deepcopy(updated)

    async def find_active_for_session(self, session_id: str) -> RunRecord | None:
        async with self._lock:
            candidates = [
                run for run in self._runs.values() if run.session_id == session_id and not run.is_terminal
            ]
            if not candidates:
                return None
            return copy.deepcopy(max(candidates, key=lambda run: run.created_at))

    async def latest_run_for_session(self, session_id: str) -> RunRecord | None:
        async with self._lock:
            candidates = [run for run in self._runs.values() if run.session_id == session_id]
            if not candidates:
                return None
            latest = max(candidates, key=lambda run: run.created_at)
            return copy.deepcopy(latest)

    async def list_runs(
        self,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        status: RunStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> RunPage:
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        async with self._lock:
            candidates = [run for run in self._runs.values() if run.user_id == user_id] if user_id else list(self._runs.values())
            if session_id is not None:
                candidates = [run for run in candidates if run.session_id == session_id]
            if status is not None:
                candidates = [run for run in candidates if run.status is RunStatus(status)]
            candidates.sort(key=lambda run: run.created_at, reverse=True)
            total = len(candidates)
            page = candidates[offset : offset + limit]
            return RunPage(
                items=[copy.deepcopy(run) for run in page],
                total=total,
                limit=limit,
                offset=offset,
            )

    async def append_event(self, event: RunEvent, execution_token: int | None = None) -> RunEvent:
        if not is_known_run_event_type(event.event_type):
            raise EventVocabularyError(event.run_id, event.event_type)
        async with self._lock:
            current = self._runs.get(event.run_id)
            if current is None:
                raise RunNotFoundError(event.run_id)

            existing = self._event_ids.get((event.run_id, event.event_id))
            if existing is not None:
                return copy.deepcopy(existing)

            validate_event_write(current, execution_token, event.event_type)

            expected_sequence = current.last_sequence + 1
            sequence = expected_sequence if event.sequence is None else event.sequence
            if sequence != expected_sequence:
                raise EventSequenceConflictError(event.run_id, expected_sequence, sequence)

            stored = replace(event, sequence=sequence)
            self._events[event.run_id].append(copy.deepcopy(stored))
            self._event_ids[(event.run_id, event.event_id)] = copy.deepcopy(stored)
            self._runs[event.run_id] = replace(current, last_sequence=sequence)
            self._evict_events(event.run_id)
            return copy.deepcopy(stored)

    async def list_events(self, run_id: str, after: int = 0, limit: int = 256) -> ReplayPage:
        if after < 0:
            raise ValueError("after must be non-negative")
        if limit < 1:
            raise ValueError("limit must be positive")
        async with self._lock:
            current = self._runs.get(run_id)
            if current is None:
                raise RunNotFoundError(run_id)
            retained = self._events[run_id]
            available = [event for event in retained if event.sequence is not None and event.sequence > after]
            events = available[:limit]
            oldest = retained[0].sequence if retained else None
            has_gap = (oldest is not None and after < oldest - 1) or (
                oldest is None and after < current.last_sequence
            )
            next_after = events[-1].sequence if events else after
            unknown = tuple(
                ordered for ordered in dict.fromkeys(event.event_type for event in retained)
                if not is_known_run_event_type(ordered)
            )
            return ReplayPage(
                events=copy.deepcopy(events),
                after=after,
                oldest_sequence=oldest,
                latest_sequence=current.last_sequence,
                has_gap=has_gap,
                has_more=len(available) > len(events),
                next_after=next_after,
                unknown_event_types=unknown,
            )

    async def attach_checkpoint(
        self,
        run_id: str,
        checkpoint_id: str,
        iteration: int,
        execution_token: int | None = None,
    ) -> None:
        if iteration < 0:
            raise ValueError("iteration must be non-negative")
        if not checkpoint_id:
            raise ValueError("checkpoint_id must not be empty")
        async with self._lock:
            current = self._runs.get(run_id)
            if current is None:
                raise RunNotFoundError(run_id)
            validate_execution_token(
                run_id,
                current.status,
                execution_token,
                current.execution_token,
            )
            if current.is_terminal:
                raise RunStateConflictError(
                    run_id,
                    current.status,
                    code="run_state_conflict",
                    message=f"Run {run_id} is terminal and rejects checkpoint writes",
                )
            metadata = copy.deepcopy(current.metadata)
            metadata["checkpoint_iteration"] = iteration
            self._runs[run_id] = replace(
                current,
                checkpoint_id=checkpoint_id,
                metadata=metadata,
            )

    def _evict_events(self, run_id: str) -> None:
        if self.event_capacity is None:
            return
        retained = self._events[run_id]
        while len(retained) > self.event_capacity:
            evicted = retained.pop(0)
            self._event_ids.pop((run_id, evicted.event_id), None)
