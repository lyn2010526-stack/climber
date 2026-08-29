"""Compatibility runtime that exposes AgentEngine through the Run protocol."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

import structlog

from app.core import AgentEvent, AgentEventType, SessionStatus
from app.core.agent_engine import AgentEngine, AgentSession
from app.core.run_protocol import (
    TERMINATION_REASON_INTERRUPTED,
    TERMINATION_REASON_USER_CANCEL,
    CheckpointScopeMismatchError,
    ExecutionTokenConflictError,
    ReplayPage,
    ResumeRun,
    RunEvent,
    RunHandle,
    RunPage,
    RunProtocolError,
    RunRecord,
    RunRuntime,
    RunState,
    RunStateConflictError,
    RunStatus,
    RunStore,
    StartRun,
    termination_metadata,
)

logger = structlog.get_logger()


class AgentEngineRunAdapter(RunRuntime):
    """Adapt the legacy AgentEngine stream to durable unified Run semantics."""

    def __init__(self, engine: AgentEngine, store: RunStore) -> None:
        self.engine = engine
        self.store = store
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._handles: dict[str, RunHandle] = {}

    async def start(self, command: StartRun) -> RunHandle:
        """Create and start one Run for the requested Agent session."""
        session = self._get_session(command.session_id)
        self._validate_session(session, command.user_id)

        lock = self._session_locks.setdefault(command.session_id, asyncio.Lock())
        async with lock:
            active = await self._active_run_for_session(command.session_id, command.user_id)
            if active is not None:
                if self._is_stale_run(active):
                    await self._recover_stale_run(active)
                else:
                    raise RunStateConflictError(
                        active.run_id,
                        active.status,
                        code="run_conflict",
                        message=f"Session {command.session_id} already has an active Run",
                    )

            run_id = str(uuid4())
            trace_id = command.trace_id or str(uuid4())
            metadata = dict(command.metadata)
            if command.message is not None:
                message_payload = command.message.to_dict()
                message_payload["run_id"] = run_id
                metadata["message"] = message_payload
            run = await self.store.create(
                RunRecord(
                    run_id=run_id,
                    session_id=command.session_id,
                    user_id=command.user_id,
                    agent_id=command.agent_id or getattr(session, "agent_id", None),
                    kind=command.kind,
                    trace_id=trace_id,
                    metadata=metadata,
                )
            )
            running = await self.store.transition(
                run.run_id,
                RunStatus.PENDING,
                RunStatus.RUNNING,
            )
            handle = RunHandle(
                run_id=running.run_id,
                session_id=running.session_id,
                execution_token=running.execution_token,
            )
            self._handles[run_id] = handle
            return handle

    def stream(self, handle: RunHandle) -> AsyncIterator[RunEvent]:
        """Execute the legacy stream while persisting every emitted event."""
        return self._stream(handle)

    async def _stream(self, handle: RunHandle) -> AsyncIterator[RunEvent]:
        run = await self.store.require(handle.run_id)
        self._check_handle(handle, run)
        session = self._get_session(run.session_id)
        self._validate_session(session, run.user_id)

        terminal_status: RunStatus | None = None
        terminal_error: dict[str, Any] | None = None
        try:
            message = self._message_for_run(run)
            async for agent_event in self.engine.run(
                session,
                message,
                run_id=run.run_id,
                trace_id=run.trace_id,
            ):
                current = await self.store.require(run.run_id)
                if handle.execution_token != current.execution_token:
                    raise ExecutionTokenConflictError(
                        run.run_id,
                        current.status,
                        handle.execution_token,
                        current.execution_token,
                    )
                if current.status is RunStatus.CANCELLED:
                    terminal_status = RunStatus.CANCELLED
                    yield self._stopped_event(current)
                    break
                self._check_handle(handle, current)
                unified = await self._persist_agent_event(agent_event, current)
                yield unified

                if agent_event.type is AgentEventType.ERROR:
                    terminal_status = RunStatus.FAILED
                    error_text = str(agent_event.data.get("error", "Agent execution failed"))
                    terminal_error = {"code": "agent_error", "message": error_text}
                    break
                if agent_event.type is AgentEventType.STOPPED:
                    terminal_status = RunStatus.CANCELLED
                    break
                if agent_event.type is AgentEventType.DONE:
                    terminal_status = self._status_from_done_event(agent_event)
                    break

            if terminal_status is None:
                terminal_status = self._status_from_session(session)
            await self._finish(run.run_id, handle.execution_token, terminal_status, error=terminal_error)
        except asyncio.CancelledError:
            await self._finish(run.run_id, handle.execution_token, RunStatus.CANCELLED)
            raise
        except Exception as exc:
            current = await self.store.get(run.run_id)
            if current is not None and current.status is RunStatus.RUNNING:
                error_event = AgentEvent(
                    type=AgentEventType.ERROR,
                    data={"error": str(exc)},
                )
                try:
                    unified = await self._persist_agent_event(error_event, current)
                    yield unified
                except Exception:
                    logger.warning(
                        "agent_run_adapter.error_event_persist_failed",
                        run_id=run.run_id,
                        error=str(exc),
                    )
                await self._finish(
                    run.run_id,
                    handle.execution_token,
                    RunStatus.FAILED,
                    error={"code": "adapter_error", "message": str(exc)},
                )
            raise
        finally:
            self._handles.pop(handle.run_id, None)

    async def resume(self, command: ResumeRun) -> RunHandle:
        run = await self.store.require(command.run_id)
        if run.session_id != command.session_id or run.user_id != command.user_id:
            raise RunStateConflictError(
                command.run_id,
                run.status,
                code="forbidden",
                message=f"Run {command.run_id} does not belong to this session or user",
            )
        if command.checkpoint_id and run.checkpoint_id != command.checkpoint_id:
            raise CheckpointScopeMismatchError(command.run_id, command.checkpoint_id)
        running = await self.store.transition(
            run.run_id,
            run.status,
            RunStatus.RUNNING,
            execution_token=command.execution_token,
        )
        handle = RunHandle(
            run_id=running.run_id,
            session_id=running.session_id,
            execution_token=running.execution_token,
        )
        self._handles[run.run_id] = handle
        return handle

    async def cancel(self, run_id: str, actor_id: str) -> RunState:
        run = await self.store.require(run_id)
        if run.user_id and run.user_id != actor_id:
            raise RunStateConflictError(
                run_id,
                run.status,
                code="forbidden",
                message=f"Actor {actor_id} cannot cancel Run {run_id}",
            )
        session = self._get_session(run.session_id)
        stop = getattr(session, "stop", None)
        if callable(stop):
            stop()
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return run
        return await self.store.transition(
            run_id,
            run.status,
            RunStatus.CANCELLED,
            values={"metadata": termination_metadata(TERMINATION_REASON_USER_CANCEL)},
            execution_token=run.execution_token,
        )

    async def replay(self, run_id: str, after: int = 0, limit: int = 256) -> ReplayPage:
        return await self.store.list_events(run_id, after=after, limit=limit)

    async def require_run(self, run_id: str) -> RunRecord:
        """Fetch a single Run, raising RunNotFoundError when absent."""
        return await self.store.require(run_id)

    async def list_runs(
        self,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        status: RunStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> RunPage:
        return await self.store.list_runs(
            session_id=session_id,
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def _persist_agent_event(self, event: AgentEvent, run: RunRecord) -> RunEvent:
        checkpoint_id = self._checkpoint_id(event, run)
        if checkpoint_id is not None:
            iteration = int(event.data.get("iteration", 0) or 0)
            await self.store.attach_checkpoint(
                run.run_id,
                checkpoint_id,
                iteration,
                execution_token=run.execution_token,
            )

        data = dict(event.data)
        if checkpoint_id is not None:
            data.setdefault("checkpoint_id", checkpoint_id)
        return await self.store.append_event(
            RunEvent(
                event_id=str(uuid4()),
                run_id=run.run_id,
                sequence=None,
                event_type=event.type.value,
                data=data,
                created_at=datetime.now(UTC),
                trace_id=run.trace_id,
                checkpoint_id=checkpoint_id,
            ),
            execution_token=run.execution_token,
        )

    async def _finish(
        self,
        run_id: str,
        execution_token: int,
        status: RunStatus,
        error: dict[str, Any] | None = None,
    ) -> None:
        current = await self.store.get(run_id)
        if current is None or current.status is status:
            return
        if current.status is not RunStatus.RUNNING:
            return
        if current.execution_token != execution_token:
            return
        values: dict[str, Any] = {}
        if error:
            values["error"] = error
            values["error_message"] = str(error.get("message") or error.get("code") or "")
        await self.store.transition(
            run_id,
            RunStatus.RUNNING,
            status,
            values=values or None,
            execution_token=execution_token,
        )

    @staticmethod
    def _status_from_done_event(event: AgentEvent) -> RunStatus:
        value = str(event.data.get("status", RunStatus.COMPLETED.value))
        if value == "max_iterations_reached":
            return RunStatus.FAILED
        if value in {status.value for status in RunStatus}:
            return RunStatus(value)
        return RunStatus.COMPLETED

    @staticmethod
    def _status_from_session(session: AgentSession) -> RunStatus:
        value = getattr(getattr(session, "status", None), "value", "completed")
        if value == SessionStatus.STOPPED.value:
            return RunStatus.CANCELLED
        if value in {status.value for status in RunStatus}:
            return RunStatus(value)
        return RunStatus.COMPLETED

    @staticmethod
    def _checkpoint_id(event: AgentEvent, run: RunRecord) -> str | None:
        if event.type is not AgentEventType.CHECKPOINT:
            return None
        supplied = event.data.get("checkpoint_id")
        if supplied:
            return str(supplied)
        iteration = int(event.data.get("iteration", 0) or 0)
        if iteration < 0:
            return None
        identity = f"climber-checkpoint:{run.session_id}:{run.run_id}:{iteration}"
        return str(uuid5(NAMESPACE_URL, identity))

    @staticmethod
    def _message_for_run(run: RunRecord) -> str:
        message = run.metadata.get("message")
        if message is None:
            return ""
        if isinstance(message, Mapping):
            return str(message.get("content", ""))
        return str(message)

    def _get_session(self, session_id: str) -> AgentSession:
        session = self.engine.get_session(session_id)
        if session is None:
            raise RunStateConflictError(
                session_id,
                RunStatus.PENDING,
                code="session_not_found",
                message=f"Session {session_id} was not found",
            )
        return session

    @staticmethod
    def _validate_session(session: AgentSession, user_id: str) -> None:
        session_user_id = getattr(session, "user_id", None)
        if session_user_id and session_user_id != user_id:
            raise RunStateConflictError(
                session.session_id,
                RunStatus.PENDING,
                code="forbidden",
                message=f"Session {session.session_id} belongs to another user",
            )

    async def _active_run_for_session(self, session_id: str, user_id: str) -> RunRecord | None:
        finder = getattr(self.store, "find_active_for_session", None)
        if finder is None:
            return None
        active = await finder(session_id)
        if active is None:
            return None
        if active.user_id and user_id and active.user_id != user_id:
            return None
        return active

    def _is_stale_run(self, run: RunRecord) -> bool:
        """True when no executor owned by this process is driving the Run.

        Single-process crash recovery: after a restart, persisted active Runs
        have no live stream and must not block the session forever. Under a
        multi-replica deployment another replica may legitimately own the Run,
        so this check is authoritative only for the current process.
        """
        if run.run_id in self._handles:
            return False
        lock = self.engine.get_session_lock(run.session_id)
        return lock is None or not lock.locked()

    async def _recover_stale_run(self, run: RunRecord) -> None:
        logger.warning(
            "agent_run_adapter.stale_run_recovery",
            run_id=run.run_id,
            status=run.status.value,
            session_id=run.session_id,
        )
        try:
            await self.store.transition(
                run.run_id,
                run.status,
                RunStatus.FAILED,
                values={
                    "error": {
                        "code": "stale_run",
                        "message": "Run had no live executor and was marked failed",
                    },
                    "error_message": "Stale Run recovered after losing its executor",
                    "metadata": termination_metadata(
                        TERMINATION_REASON_INTERRUPTED,
                        detail="stale_run",
                    ),
                },
            )
        except RunProtocolError as exc:
            logger.warning(
                "agent_run_adapter.stale_run_recovery_failed",
                run_id=run.run_id,
                error=str(exc),
            )

    @staticmethod
    def _stopped_event(run: RunRecord) -> RunEvent:
        """Client-compatibility terminal event for an already cancelled Run.

        Business events cannot be persisted once the Run is terminal, so this
        event is delivered to the live stream only; replay consumers observe
        the terminal Run status instead.
        """
        return RunEvent(
            event_id=str(uuid4()),
            run_id=run.run_id,
            sequence=None,
            event_type=AgentEventType.STOPPED.value,
            data={"reason": "user_requested"},
            created_at=datetime.now(UTC),
            trace_id=run.trace_id,
        )

    @staticmethod
    def _check_handle(handle: RunHandle, run: RunRecord) -> None:
        if handle.execution_token != run.execution_token:
            raise ExecutionTokenConflictError(
                run.run_id,
                run.status,
                handle.execution_token,
                run.execution_token,
            )
        if run.status is not RunStatus.RUNNING:
            raise RunStateConflictError(
                run.run_id,
                run.status,
                code="run_state_conflict",
                message=f"Run {run.run_id} is not running",
            )


__all__ = ["AgentEngineRunAdapter"]
