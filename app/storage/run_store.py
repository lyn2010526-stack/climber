"""SQLAlchemy persistence adapter for the unified Run protocol."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog import get_logger

from app.core.raw_payload import RawPayloadSnapshot
from app.core.run_protocol import (
    RUN_TRANSITION_FIELDS,
    TERMINAL_RUN_STATUSES,
    EventSequenceConflictError,
    EventVocabularyError,
    ExecutionTokenConflictError,
    ReplayPage,
    RunEvent,
    RunNotFoundError,
    RunPage,
    RunRecord,
    RunStateConflictError,
    RunStatus,
    is_audit_event_type,
    is_known_run_event_type,
    validate_event_write,
    validate_execution_token,
    validate_run_transition,
)
from app.storage import async_session
from app.storage.database import CheckpointRecord, RawPayloadRecord, RunEventRecord, Turn

SessionFactory = Callable[[], AsyncSession]

logger = get_logger()


def _to_database_datetime(value: datetime | None) -> datetime | None:
    """Store UTC timestamps as naive values for the existing DB schema."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _from_database_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _encode_error(error: Mapping[str, Any] | None) -> str | None:
    if error is None:
        return None
    return json.dumps(dict(error), ensure_ascii=False)


def _decode_error(error: str | None) -> dict[str, Any] | None:
    if error is None:
        return None
    try:
        decoded = json.loads(error)
    except (TypeError, ValueError):
        return {"message": error}
    return decoded if isinstance(decoded, dict) else {"value": decoded}


def _copy_json(value: Any) -> Any:
    return copy.deepcopy(value)


class SQLAlchemyRunStore:
    """Durable RunStore backed by the application's async SQLAlchemy engine."""

    _TRANSITION_FIELDS = RUN_TRANSITION_FIELDS

    def __init__(self, session_factory: SessionFactory | async_sessionmaker[AsyncSession] | None = None) -> None:
        self._session_factory = session_factory or async_session

    async def create(self, run: RunRecord) -> RunRecord:
        async with self._session_factory() as db:
            existing = await db.scalar(select(Turn).where(Turn.id == run.run_id))
            if existing is not None:
                raise RunStateConflictError(
                    run.run_id,
                    RunStatus(existing.status),
                    code="run_conflict",
                    message=f"Run {run.run_id} already exists",
                )

            record = Turn(
                id=run.run_id,
                session_id=run.session_id,
                user_id=run.user_id,
                agent_id=run.agent_id,
                kind=run.kind,
                status=run.status.value,
                checkpoint_id=run.checkpoint_id,
                trace_id=run.trace_id,
                last_sequence=run.last_sequence,
                execution_token=run.execution_token,
                parent_run_id=run.parent_run_id,
                started_at=_to_database_datetime(run.started_at),
                completed_at=_to_database_datetime(run.completed_at),
                error=_encode_error(run.error),
                error_message=run.error_message,
                metadata_=_copy_json(run.metadata),
                created_at=_to_database_datetime(run.created_at),
            )
            if record.status == RunStatus.RUNNING.value and record.started_at is None:
                record.started_at = _to_database_datetime(datetime.now(UTC))
                record.execution_token = max(record.execution_token, 1)

            db.add(record)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                existing = await db.scalar(select(Turn).where(Turn.id == run.run_id))
                if existing is not None:
                    raise RunStateConflictError(
                        run.run_id,
                        RunStatus(existing.status),
                        code="run_conflict",
                        message=f"Run {run.run_id} already exists",
                    ) from None
                raise
            return self._to_run(record)

    async def get(self, run_id: str) -> RunRecord | None:
        async with self._session_factory() as db:
            record = await db.scalar(select(Turn).where(Turn.id == run_id))
            return self._to_run(record) if record is not None else None

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
        supplied = dict(values or {})
        unknown = set(supplied) - self._TRANSITION_FIELDS
        if unknown:
            raise ValueError(f"Unsupported Run fields: {sorted(unknown)}")

        async with self._session_factory() as db:
            current = await self._load_run(db, run_id)
            self._check_transition(current, expected_status, target_status, execution_token)
            update_values = self._transition_values(current, target_status, supplied)

            statement = (
                update(Turn)
                .where(
                    Turn.id == run_id,
                    Turn.status == expected_status.value,
                    Turn.execution_token == current.execution_token,
                )
                .values(**update_values)
            )
            result = await db.execute(statement)
            if result.rowcount != 1:
                await db.rollback()
                current = await self.require(run_id)
                self._check_transition(current, expected_status, target_status, execution_token)
                raise RunStateConflictError(
                    run_id,
                    current.status,
                    expected=expected_status,
                    target=target_status,
                )

            await db.commit()
            updated = await db.scalar(select(Turn).where(Turn.id == run_id))
            if updated is None:
                raise RunNotFoundError(run_id)
            return self._to_run(updated)

    async def append_event(self, event: RunEvent, execution_token: int | None = None) -> RunEvent:
        if not is_known_run_event_type(event.event_type):
            raise EventVocabularyError(event.run_id, event.event_type)
        async with self._session_factory() as db:
            for _attempt in range(5):
                current = await self._load_run(db, event.run_id)
                existing = await db.scalar(
                    select(RunEventRecord).where(
                        RunEventRecord.run_id == event.run_id,
                        RunEventRecord.event_id == event.event_id,
                    )
                )
                if existing is not None:
                    stored_event = self._to_event(existing)
                    await db.rollback()
                    return stored_event

                self._check_event_write(current, execution_token, event)
                expected_sequence = current.last_sequence + 1
                if event.sequence is not None and event.sequence != expected_sequence:
                    raise EventSequenceConflictError(event.run_id, expected_sequence, event.sequence)

                statement = (
                    update(Turn)
                    .where(
                        Turn.id == event.run_id,
                        Turn.status == current.status.value,
                        Turn.last_sequence == current.last_sequence,
                        Turn.execution_token == current.execution_token,
                    )
                    .values(last_sequence=expected_sequence)
                )
                result = await db.execute(statement)
                if result.rowcount != 1:
                    await db.rollback()
                    refreshed = await self.require(event.run_id)
                    if event.sequence is not None:
                        raise EventSequenceConflictError(event.run_id, refreshed.last_sequence + 1, event.sequence)
                    if execution_token is not None and execution_token != refreshed.execution_token:
                        raise ExecutionTokenConflictError(
                            event.run_id,
                            refreshed.status,
                            execution_token,
                            refreshed.execution_token,
                        )
                    if refreshed.is_terminal and not self._is_audit_event(event):
                        raise RunStateConflictError(
                            event.run_id,
                            refreshed.status,
                            code="run_state_conflict",
                            message=f"Run {event.run_id} is terminal and rejects business events",
                        )
                    continue

                stored = RunEventRecord(
                    id=str(uuid4()),
                    run_id=event.run_id,
                    event_id=event.event_id,
                    sequence=expected_sequence,
                    event_type=event.event_type,
                    data=_copy_json(event.data),
                    created_at=_to_database_datetime(event.created_at),
                    trace_id=event.trace_id,
                    checkpoint_id=event.checkpoint_id,
                    execution_token=current.execution_token,
                )
                db.add(stored)
                try:
                    await db.commit()
                except IntegrityError:
                    await db.rollback()
                    duplicate = await db.scalar(
                        select(RunEventRecord).where(
                            RunEventRecord.run_id == event.run_id,
                            RunEventRecord.event_id == event.event_id,
                        )
                    )
                    if duplicate is not None:
                        return self._to_event(duplicate)
                    if event.sequence is not None:
                        current = await self.require(event.run_id)
                        raise EventSequenceConflictError(event.run_id, current.last_sequence + 1, event.sequence) from None
                    continue
                return self._to_event(stored)

            current = await self.require(event.run_id)
            raise RunStateConflictError(
                event.run_id,
                current.status,
                code="event_write_conflict",
                message=f"Event write for Run {event.run_id} conflicted repeatedly",
            )

    async def list_events(self, run_id: str, after: int = 0, limit: int = 256) -> ReplayPage:
        if after < 0:
            raise ValueError("after must be non-negative")
        if limit < 1:
            raise ValueError("limit must be positive")

        async with self._session_factory() as db:
            current = await self._load_run(db, run_id)
            oldest = await db.scalar(
                select(RunEventRecord.sequence)
                .where(RunEventRecord.run_id == run_id)
                .order_by(RunEventRecord.sequence.asc())
                .limit(1)
            )
            records = (
                await db.scalars(
                    select(RunEventRecord)
                    .where(RunEventRecord.run_id == run_id, RunEventRecord.sequence > after)
                    .order_by(RunEventRecord.sequence.asc())
                    .limit(limit + 1)
                )
            ).all()
            has_more = len(records) > limit
            events = [self._to_event(record) for record in records[:limit]]
            has_gap = (oldest is not None and after < oldest - 1) or (
                oldest is None and after < current.last_sequence
            )
            event_types = (
                await db.scalars(
                    select(RunEventRecord.event_type)
                    .where(RunEventRecord.run_id == run_id)
                    .distinct()
                    .order_by(RunEventRecord.event_type.asc())
                )
            ).all()
            unknown = tuple(name for name in event_types if not is_known_run_event_type(name))
            if unknown:
                logger.warning(
                    "run_store.unknown_event_types",
                    run_id=run_id,
                    unknown_event_types=list(unknown),
                )
            return ReplayPage(
                events=events,
                after=after,
                oldest_sequence=oldest,
                latest_sequence=current.last_sequence,
                has_gap=has_gap,
                has_more=has_more,
                next_after=events[-1].sequence if events else after,
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

        async with self._session_factory() as db:
            current = await self._load_run(db, run_id)
            self._check_execution_token(current, execution_token)
            if current.is_terminal:
                raise RunStateConflictError(
                    run_id,
                    current.status,
                    code="run_state_conflict",
                    message=f"Run {run_id} is terminal and rejects checkpoint writes",
                )
            checkpoint = await db.scalar(select(CheckpointRecord).where(CheckpointRecord.id == checkpoint_id))
            if checkpoint is None:
                logger.warning(
                    "run_store.checkpoint_record_missing",
                    run_id=run_id,
                    checkpoint_id=checkpoint_id,
                )
            elif (
                checkpoint.session_id != current.session_id
                or bool(checkpoint.thread_id and checkpoint.thread_id != run_id)
            ):
                from app.core.run_protocol import CheckpointScopeMismatchError

                raise CheckpointScopeMismatchError(run_id, checkpoint_id)

            metadata = _copy_json(current.metadata)
            metadata["checkpoint_iteration"] = iteration
            statement = (
                update(Turn)
                .where(
                    Turn.id == run_id,
                    Turn.status == current.status.value,
                    Turn.execution_token == current.execution_token,
                )
                .values(checkpoint_id=checkpoint_id, metadata_=metadata)
            )
            result = await db.execute(statement)
            if result.rowcount != 1:
                await db.rollback()
                refreshed = await self.require(run_id)
                self._check_execution_token(refreshed, execution_token)
                raise RunStateConflictError(
                    run_id,
                    refreshed.status,
                    code="run_state_conflict",
                    message=f"Run {run_id} changed while attaching checkpoint",
                )
            await db.commit()

    async def find_active_for_session(self, session_id: str) -> RunRecord | None:
        active_statuses = tuple(
            status.value
            for status in (RunStatus.PENDING, RunStatus.RUNNING, RunStatus.PAUSED)
        )
        async with self._session_factory() as db:
            record = await db.scalar(
                select(Turn)
                .where(Turn.session_id == session_id, Turn.status.in_(active_statuses))
                .order_by(Turn.created_at.desc())
                .limit(1)
            )
            return self._to_run(record) if record is not None else None

    async def latest_run_for_session(self, session_id: str) -> RunRecord | None:
        async with self._session_factory() as db:
            record = await db.scalar(
                select(Turn)
                .where(Turn.session_id == session_id)
                .order_by(Turn.created_at.desc())
                .limit(1)
            )
            return self._to_run(record) if record is not None else None

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
        async with self._session_factory() as db:
            stmt = select(Turn)
            if session_id is not None:
                stmt = stmt.where(Turn.session_id == session_id)
            if user_id is not None:
                stmt = stmt.where(Turn.user_id == user_id)
            if status is not None:
                stmt = stmt.where(Turn.status == status.value)
            total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
            records = (
                (
                    await db.execute(
                        stmt.order_by(Turn.created_at.desc(), Turn.id.desc()).offset(offset).limit(limit)
                    )
                )
                .scalars()
                .all()
            )
            return RunPage(
                items=[self._to_run(record) for record in records],
                total=int(total or 0),
                limit=limit,
                offset=offset,
            )

    async def save_raw_payload(self, snapshot: RawPayloadSnapshot) -> RawPayloadRecord:
        record = RawPayloadRecord(
            run_id=snapshot.run_id,
            message_id=snapshot.message_id,
            provider=snapshot.provider,
            standard_fields=_copy_json(snapshot.standard_fields),
            payload_digest=snapshot.payload_digest,
            payload_ciphertext=snapshot.payload_ciphertext,
            redaction_version=snapshot.redaction_version,
            expires_at=_to_database_datetime(snapshot.expires_at),
        )
        async with self._session_factory() as db:
            db.add(record)
            await db.commit()
            await db.refresh(record)
        return record

    async def list_raw_payloads(self, run_id: str) -> list[RawPayloadRecord]:
        async with self._session_factory() as db:
            records = (
                await db.scalars(
                    select(RawPayloadRecord)
                    .where(RawPayloadRecord.run_id == run_id)
                    .order_by(RawPayloadRecord.created_at.asc())
                )
            ).all()
            return list(records)

    async def _load_run(self, db: AsyncSession, run_id: str) -> RunRecord:
        record = await db.scalar(select(Turn).where(Turn.id == run_id))
        if record is None:
            raise RunNotFoundError(run_id)
        return self._to_run(record)

    @staticmethod
    def _check_execution_token(current: RunRecord, execution_token: int | None) -> None:
        validate_execution_token(
            current.run_id,
            current.status,
            execution_token,
            current.execution_token,
        )

    def _check_transition(
        self,
        current: RunRecord,
        expected: RunStatus,
        target: RunStatus,
        execution_token: int | None,
    ) -> None:
        validate_run_transition(current, expected, target, execution_token)

    @staticmethod
    def _transition_values(
        current: RunRecord,
        target: RunStatus,
        supplied: dict[str, Any],
    ) -> dict[str, Any]:
        metadata = _copy_json(current.metadata)
        if "metadata" in supplied:
            metadata.update(_copy_json(supplied.pop("metadata") or {}))

        values: dict[str, Any] = {"status": target.value, "metadata_": metadata}
        for field_name, value in supplied.items():
            if field_name == "error":
                values["error"] = _encode_error(value)
            elif field_name in {"started_at", "completed_at"}:
                values[field_name] = _to_database_datetime(value)
            else:
                values[field_name] = value

        if target is RunStatus.RUNNING:
            values.setdefault("started_at", _to_database_datetime(current.started_at or datetime.now(UTC)))
            values.setdefault("completed_at", None)
            values.setdefault("error", None)
            values.setdefault("error_message", None)
            values["execution_token"] = current.execution_token + 1
        elif target in TERMINAL_RUN_STATUSES:
            values.setdefault("completed_at", _to_database_datetime(datetime.now(UTC)))
        return values

    @staticmethod
    def _is_audit_event(event: RunEvent) -> bool:
        return is_audit_event_type(event.event_type)

    def _check_event_write(
        self,
        current: RunRecord,
        execution_token: int | None,
        event: RunEvent,
    ) -> None:
        validate_event_write(current, execution_token, event.event_type)

    @staticmethod
    def _to_run(record: Turn) -> RunRecord:
        return RunRecord(
            run_id=record.id,
            session_id=record.session_id,
            user_id=record.user_id or "",
            kind=record.kind or "agent_chat",
            status=RunStatus(record.status),
            agent_id=record.agent_id,
            trace_id=record.trace_id,
            checkpoint_id=record.checkpoint_id,
            last_sequence=record.last_sequence or 0,
            execution_token=record.execution_token or 0,
            started_at=_from_database_datetime(record.started_at),
            completed_at=_from_database_datetime(record.completed_at),
            error=_decode_error(record.error),
            error_message=record.error_message,
            metadata=_copy_json(record.metadata_ or {}),
            parent_run_id=record.parent_run_id,
            created_at=_from_database_datetime(record.created_at) or datetime.now(UTC),
        )

    @staticmethod
    def _to_event(record: RunEventRecord) -> RunEvent:
        return RunEvent(
            event_id=record.event_id,
            run_id=record.run_id,
            sequence=record.sequence,
            event_type=record.event_type,
            data=_copy_json(record.data or {}),
            created_at=_from_database_datetime(record.created_at) or datetime.now(UTC),
            trace_id=record.trace_id,
            checkpoint_id=record.checkpoint_id,
        )

    async def cleanup_expired_raw_payloads(self, *, now: datetime | None = None) -> int:
        """Delete raw payload records whose `expires_at` has passed.

        `debug`-policy payloads carry an `expires_at`; `standard` payloads keep
        `expires_at = None` and are never reclaimed by this pass. Returns the
        number of rows deleted.
        """
        now = now or datetime.now(UTC)
        async with self._session_factory() as db:
            result = await db.execute(
                delete(RawPayloadRecord).where(
                    RawPayloadRecord.expires_at.is_not(None),
                    RawPayloadRecord.expires_at < _to_database_datetime(now),
                )
            )
            await db.commit()
        return int(result.rowcount or 0)
