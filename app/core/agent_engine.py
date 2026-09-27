"""Minimal agent engine with ReAct loop.

This module provides the AgentEngine class that orchestrates agent execution
with tool validation, streaming, and checkpoint management.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
import time
from collections.abc import (
    AsyncIterator,  # noqa: TC003  # no `from __future__ import annotations`; evaluated at runtime
)
from dataclasses import replace
from typing import Any
from uuid import uuid4

import structlog

from app.core import (
    AgentEvent,
    AgentEventType,
    ChatResult,
    ContextConfig,
    MessageRole,
)
from app.core.checkpoint import (
    CheckpointData,
    InMemoryCheckpointStore,
    SQLiteCheckpointStore,
    sanitize_checkpoint,
)
from app.core.compressor import ContextCompressor, estimate_tokens
from app.core.di import resolve as di_resolve
from app.core.engine.persistence import persist_message
from app.core.engine.run_storage import RunStorage, track_run
from app.core.engine.session_runner import merge_stream_chunk, response_usage
from app.core.engine.tools import DEFAULT_MAX_TOOLS_IN_PROMPT, build_tools
from app.core.engine.validation import (
    _COMMAND_TOOLS,
    _FILE_TOOLS,
    _approval_key,
    make_tool_call_id,
    validate_tool_call,
)
from app.core.parallel import DEFAULT_MAX_RESULT_CHARS, ParallelToolExecutor, truncate_tool_result
from app.core.persistent_memory import PersistentMemoryService
from app.core.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    ResourceTracker,
    RetryExhaustedError,
    TimeoutConfig,
)
from app.core.session import AgentSession, SessionConfig
from app.core.tool_prioritizer import ToolPrioritizer
from app.models.registry import ModelRegistry
from app.tools import ToolRegistry

logger = structlog.get_logger()


# Markers for per-turn injected system content. These blocks change every turn
# (fresh lessons, fresh graph context), so they must stay out of any cached
# prompt prefix: Anthropic hashes the whole system block, and one changed
# character invalidates the cache for the entire request.
DYNAMIC_SYSTEM_MARKERS = ("<!-- LESSONS -->", "<!-- GRAPH_CONTEXT -->")
LESSONS_MARKER = DYNAMIC_SYSTEM_MARKERS[0]
GRAPH_CONTEXT_MARKER = DYNAMIC_SYSTEM_MARKERS[1]


DEFAULT_MAX_SESSIONS = 128


class _CheckpointUnavailable(RuntimeError):
    """A durable checkpoint could not be written, so the run cannot be trusted.

    Raised with the store's own exception as its cause, so the original class
    (``RuntimeError``, ``OSError``, a driver error) stays observable. It exists
    only to separate "the checkpoint store is broken" from "the agent failed":
    the first must abort the run loudly, the second is an ordinary outcome the
    caller reports as a failed turn.
    """


def _parse_max_sessions(raw: Any) -> int:
    """Resolve the session cap, falling back to the default on bad input.

    A malformed environment value must never disable the cap, so anything
    unparsable or non-positive yields DEFAULT_MAX_SESSIONS.

    Args:
        raw: The raw configuration value.

    Returns:
        A positive session cap.
    """
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_MAX_SESSIONS
    if value <= 0:
        return DEFAULT_MAX_SESSIONS
    return value


def _observability_sinks():
    """Return the shared trace collector and audit chain.

    ``TraceCollector`` and ``AuditChain`` had no production writer, so
    ``/observability/traces`` and ``/observability/audit`` always answered with
    an empty list while the engine did its work unrecorded. The engine is the
    place that knows what happened, so it writes here.

    Returns:
        A ``(collector, audit_chain)`` tuple, or ``(None, None)`` when
        observability storage is unavailable. Instrumentation must never be the
        reason a task fails.
    """
    try:
        from app.core.observability.api import get_audit_chain, get_trace_collector

        return get_trace_collector(), get_audit_chain()
    except Exception as exc:
        logger.warning(
            "observability_sinks_unavailable",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return None, None


def _alignment_tracker():
    """Return the shared alignment tracker when observability is available."""
    try:
        from app.core.observability.api import get_goal_tracker

        return get_goal_tracker()
    except Exception as exc:
        logger.warning(
            "alignment_tracker_unavailable",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return None


def _record_audit(
    audit_chain: Any,
    decision_type: str,
    *,
    session_id: str = "",
    input_summary: str = "",
    output_summary: str = "",
    rationale: str = "",
    confidence: float = 0.0,
) -> None:
    """Append one audit entry, swallowing storage failures."""
    if audit_chain is None:
        return
    try:
        audit_chain.log_decision(
            decision_type=decision_type,
            input_summary=input_summary[:500],
            output_summary=output_summary[:500],
            rationale=rationale[:500],
            confidence=confidence,
            session_id=session_id,
        )
    except Exception:
        logger.debug("audit_log_failed", decision_type=decision_type)


def _record_span_event(collector: Any, span: Any, event: Any) -> None:
    """Attach one engine event to the active trace span, ignoring failures."""
    if collector is None or span is None:
        return
    try:
        event_type = getattr(event.type, "value", str(event.type))
        collector.add_event(
            span,
            event_type,
            {"data": _jsonable(getattr(event, "data", {}))},
        )
    except Exception:
        logger.debug("trace_event_failed")


def _jsonable(value: Any) -> Any:
    """Best-effort conversion of event payloads into JSON-serialisable data."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _emergency_stop_active() -> bool:
    """Return True when a global emergency stop forbids new executions.

    Delegates to ``execution_blocked``, the single gate every execution entry
    point shares, so the engine and the workflow/crew/collaboration paths can
    never disagree about whether the kill switch is engaged.
    """
    from app.core.observability.emergency_stop import execution_blocked

    return execution_blocked() is not None


def _record_usage(result: Any, adapter: Any, session: AgentSession) -> None:
    """Feed a model result into the token usage counter.

    TOKEN_USAGE existed but had no write point, so token spend was invisible
    on /metrics. Every failure is contained: metrics must never break a
    completed model call.

    Args:
        result: The ChatResult returned by the adapter.
        adapter: The adapter, used to name the provider.
        session: The session the call belonged to.
    """
    if result is None:
        return
    try:
        from app.middleware.metrics import record_token_usage

        provider = getattr(adapter, "provider", None) or type(adapter).__name__
        model_id = (
            getattr(adapter, "_model_id", None)
            or getattr(adapter, "model_id", None)
            or session.model_id
            or ""
        )
        record_token_usage(
            provider=str(provider),
            model_id=str(model_id),
            usage=getattr(result, "usage", None),
        )
    except Exception:  # pragma: no cover - never fail a completed call
        return


def _resolve_registry(service_name: str, factory: Any) -> Any:
    """Resolve a registry from DI, falling back to a fresh instance."""
    try:
        return di_resolve(service_name)
    except Exception:
        return factory()


class AgentEngine:
    """Core agent execution engine with ReAct loop."""

    # Tool categories used for plan-mode validation and sandbox checks
    _COMMAND_TOOLS: set[str] = _COMMAND_TOOLS
    _FILE_TOOLS: dict[str, tuple[str, str]] = _FILE_TOOLS
    permission_timeout_seconds: float = 30.0

    def __init__(
        self,
        model_registry: Any = None,
        tool_registry: Any = None,
        checkpoint_store: InMemoryCheckpointStore | SQLiteCheckpointStore | None = None,
        run_store: RunStorage | None = None,
    ) -> None:
        self.model_registry = model_registry or _resolve_registry("ModelRegistry", ModelRegistry)
        self.tool_registry = tool_registry or _resolve_registry("ToolRegistry", ToolRegistry)
        # InMemory was the default, so every restart dropped all checkpoints and
        # RecoveryManager had nothing to restore from. The SQLite store is
        # already wired to the application database, so it is the safe default;
        # tests that want isolation still pass InMemoryCheckpointStore().
        self._checkpoints: Any = checkpoint_store or SQLiteCheckpointStore()
        self._run_store = run_store if run_store is not None else RunStorage()
        self._sessions: dict[str, AgentSession] = {}
        self._session_locks: dict[str, asyncio.Lock] = {}
        # Insertion-ordered mirror of _sessions. The most recent session id
        # sits last, so the first entry is the least recently used. Kept as a
        # separate list because dict ordering cannot express "recently touched"
        # without rewriting every hit.
        self._session_order: list[str] = []
        # A hard cap on resident sessions. Sessions are created by eight
        # production call sites that all drop their reference afterwards, so
        # the registry would otherwise grow for the process lifetime and keep
        # every api_key reachable. Zero disables eviction.
        self.max_sessions = _parse_max_sessions(
            os.environ.get("CLIMBER_MAX_SESSIONS", DEFAULT_MAX_SESSIONS)
        )
        # Single source for the tool-result budget, shared by the executor and
        # the debug-recovery path so both entry points cap results identically.
        self._tool_result_char_limit = DEFAULT_MAX_RESULT_CHARS
        self._background_tasks: set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()
        self.resource_tracker = ResourceTracker()
        self.memory_service = PersistentMemoryService()
        self.tool_prioritizer = ToolPrioritizer()
        self.reasoning = None
        self._init_debug_loop()
        self._init_sandbox()
        self._init_permissions()
        self._init_reasoning()

    @property
    def checkpoint_store(self) -> InMemoryCheckpointStore | SQLiteCheckpointStore:
        """The store this engine writes checkpoints to (consulted by recovery)."""
        return self._checkpoints

    def _init_reasoning(self) -> None:
        """Initialize the multi-strategy reasoning service so the /reason API works."""
        try:
            from app.core.reasoning.service import ReasoningService

            self.reasoning = ReasoningService(model_registry=self.model_registry)
        except Exception:
            self.reasoning = None

    def _init_debug_loop(self) -> None:
        """Debug loop extension point; wired when a debug engine is installed."""
        self.debug_loop = None

    def _init_sandbox(self) -> None:
        """Initialize the security sandbox."""
        try:
            import os

            from app.core.security_sandbox import (
                AgentMode,
                PermissionOverlay,
                SandboxConfig,
                SecuritySandbox,
            )
            workdir = os.environ.get("CLIMBER_SANDBOX_WORKDIR") or os.getcwd()
            self.sandbox = SecuritySandbox(SandboxConfig(workdir=workdir))
            self.permission_overlay = PermissionOverlay()
            self._setup_default_permissions()
            self.agent_mode = AgentMode.ACT
        except Exception as exc:
            # Previously silent. Command execution now fails closed in
            # validation._check_sandbox when sandbox is None, so this state is
            # degraded-but-safe; it must still be visible to operators instead of
            # being discovered through a refused tool call.
            logger.error(
                "sandbox_init_failed command_execution_disabled",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            self.sandbox = None
            self.permission_overlay = None
            self.agent_mode = None

    def _init_permissions(self) -> None:
        """Initialize default permission configuration, reloading any persisted config."""
        try:
            from app.core.permission_rules import get_default_config
            persisted = self._load_permission_config()
            self._default_permission_config = persisted or get_default_config()
        except Exception:
            try:
                from app.core.permission_rules import get_default_config
                self._default_permission_config = get_default_config()
            except Exception:
                self._default_permission_config = None

    @staticmethod
    def _permission_config_path() -> str:
        import os
        data_dir = os.environ.get("CLIMBER_DATA_DIR", "data")
        return os.path.join(data_dir, "permission_config.json")

    def _load_permission_config(self) -> Any:
        """Load the persisted default permission config, if any."""
        import json
        import os
        path = self._permission_config_path()
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            from app.core.permission_rules import PermissionConfig
            return PermissionConfig.from_dict(data)
        except Exception:
            return None

    def _save_permission_config(self, config: Any) -> None:
        """Persist the default permission config so it survives restarts."""
        import json
        import os
        path = self._permission_config_path()
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as exc:
            # The in-memory permission overlay is already applied, so failing to
            # persist only means the defaults are re-seeded on next start.
            logger.debug(
                "permission_config_persist_failed",
                path=path,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    def _setup_default_permissions(self) -> None:
        """Setup default permission overlay, mirroring permission_rules DEFAULT mode."""
        from app.core.security_sandbox import PermissionLevel, PermissionRule
        defaults = [
            PermissionRule(action="read", resource_pattern="*", level=PermissionLevel.ALLOW, description="Read any file"),
            PermissionRule(action="write", resource_pattern="*", level=PermissionLevel.ASK, description="Write requires approval"),
            PermissionRule(action="execute", resource_pattern="*", level=PermissionLevel.ASK, description="Execute requires approval"),
            PermissionRule(action="delete", resource_pattern="*", level=PermissionLevel.DENY, description="Delete forbidden"),
        ]
        self.permission_overlay.set_defaults(defaults)

    def create_session(
        self,
        agent_id: str,
        user_id: str,
        provider: str,
        model_id: str,
        api_key: str,
        base_url: str | None = None,
        system_prompt: str = "",
        tools: list[str] | None = None,
        context_config: ContextConfig | None = None,
        session_id: str | None = None,
        session_config: SessionConfig | None = None,
        mode: str | None = None,
    ) -> AgentSession:
        """Create a new agent session.

        Args:
            agent_id: The agent ID.
            user_id: The user ID.
            provider: The model provider.
            model_id: The model ID.
            api_key: The API key.
            base_url: Optional base URL.
            system_prompt: Optional system prompt.
            tools: Optional list of tool names.
            context_config: Optional context configuration.
            session_id: Optional session ID (generated if not provided).
            session_config: Optional full session configuration to use as base.
            mode: Optional agent mode override.

        Returns:
            The created AgentSession instance.
        """
        from uuid import uuid4
        sid = session_id or str(uuid4())
        session = AgentSession(
            session_id=sid,
            agent_id=agent_id,
            user_id=user_id,
            provider=provider,
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
            system_prompt=system_prompt,
            tools=tools,
            context_config=context_config,
            mode=mode,
            session_config=session_config,
        )
        if hasattr(self, "_default_permission_config") and self._default_permission_config is not None:
            session.permission_config = self._default_permission_config
        if system_prompt:
            session.messages.append({"role": MessageRole.SYSTEM, "content": system_prompt})
        self._register_session(session)
        return session

    def _prompt_tool_budget(self, session: AgentSession) -> int | None:
        """Decide how many tool schemas this session may put in the prompt.

        A session that names its own tools has made an explicit choice, so
        the full list is sent. A session that leaves ``tools`` empty is asking
        for the default set, and that set is trimmed to the documented budget.

        Args:
            session: The session about to be run.

        Returns:
            The maximum tool count, or None to send every tool.
        """
        if session.tools:
            return None
        override = os.environ.get("CLIMBER_MAX_PROMPT_TOOLS")
        if override:
            try:
                value = int(override)
            except ValueError:
                return DEFAULT_MAX_TOOLS_IN_PROMPT
            return value if value > 0 else None
        return DEFAULT_MAX_TOOLS_IN_PROMPT

    def _touch_session(self, session_id: str) -> None:
        """Mark a session as most recently used.

        Args:
            session_id: Identifier of the session being used.
        """
        order = getattr(self, "_session_order", None)
        if order is None:
            return
        if session_id in order:
            order.remove(session_id)
        order.append(session_id)

    def _register_session(self, session: AgentSession) -> None:
        """Add a session to the registry and enforce the residency cap.

        Eviction reuses :meth:`close_session` so an evicted entry releases its
        lock, stops its state machine and clears ``api_key`` exactly like an
        explicit DELETE does. A session that is mid-run is never a candidate:
        its ``run()`` still holds the object, and dropping the registry entry
        would leave the iteration without a lock to acquire.

        Args:
            session: The session to register.
        """
        sid = session.session_id
        self._sessions[sid] = session
        self._touch_session(sid)
        self._evict_sessions_if_needed(protect=sid)

    def _evict_sessions_if_needed(self, protect: str | None = None) -> None:
        """Close the least recently used sessions until the cap is met.

        Args:
            protect: Session id that must survive this pass. The session being
                registered is protected, because a cap of 1 would otherwise
                evict the brand-new session before the caller ever sees it.
        """
        cap = getattr(self, "max_sessions", 0)
        if not cap or cap <= 0:
            return
        order = getattr(self, "_session_order", None)
        if order is None:
            return
        while len(self._sessions) > cap:
            victim = None
            for candidate in order:
                if candidate == protect:
                    continue
                session = self._sessions.get(candidate)
                lock = self._session_locks.get(candidate)
                if session is None or (lock is not None and lock.locked()) or self._session_is_busy(session):
                    continue
                victim = candidate
                break
            if victim is None:
                # Every remaining session is mid-run. Exceeding the cap is
                # correct here: dropping an in-flight run would strand it.
                return
            self.close_session(victim)

    @staticmethod
    def _session_is_busy(session: AgentSession) -> bool:
        """Return True while a session is mid-run and must not be evicted."""
        from app.core.task_state_machine import TaskState

        try:
            return session.state_machine.state == TaskState.RUNNING
        except Exception:
            return False

    async def run(self, session: AgentSession, message: str) -> AsyncIterator[AgentEvent]:
        """Run the agent engine for a session and message.

        Args:
            session: The agent session.
            message: The user message.

        Yields:
            AgentEvent instances during execution.
        """
        # The emergency stop documented that it blocks new task executions,
        # but nothing ever read the flag, so activating it through the REST
        # API changed nothing. This is the read.
        if _emergency_stop_active():
            yield AgentEvent(
                type=AgentEventType.ERROR,
                data={
                    "error": "Emergency stop is active; task execution is blocked",
                    "emergency_stop": True,
                },
            )
            return

        lock = self._session_locks.get(session.session_id)
        if lock is None:
            lock = asyncio.Lock()
            self._session_locks[session.session_id] = lock
        # A session that is being worked on is the most recent user of the
        # registry, so refresh its LRU position before taking the lock.
        self._touch_session(session.session_id)

        if lock.locked():
            yield AgentEvent(type=AgentEventType.ERROR, data={"error": "Session is busy processing another request"})
            return

        collector, audit_chain = _observability_sinks()
        alignment_tracker = _alignment_tracker()
        if alignment_tracker is not None:
            try:
                alignment_tracker.check_alignment(message)
            except Exception:
                logger.debug("alignment_check_failed", session_id=session.session_id)
        span = None
        if collector is not None:
            try:
                span = collector.start_span(
                    operation="agent.run",
                    tags={"session_id": session.session_id},
                )
            except Exception:
                span = None

        _record_audit(
            audit_chain,
            "agent_run_start",
            session_id=session.session_id,
            input_summary=message,
        )

        span_status = "ok"
        # Terminal events are buffered so the run store commits the turn and
        # session rows before the consumer observes DONE or ERROR.
        terminal: list[AgentEvent] = []
        # Engines assembled by harnesses via __new__ never run __init__ and own
        # no store, so their runs stay purely in-memory instead of failing on a
        # missing attribute.
        run_store = getattr(self, "_run_store", None)
        tracker = track_run(session, run_store) if run_store is not None else contextlib.nullcontext()
        try:
            # aclosing() is what forwards a consumer's GeneratorExit into the
            # run body. Without it an abandoned stream left the loop suspended
            # mid-response, so the usage the model had already reported was
            # never recorded and the turn was committed as bare.
            async with (
                lock,
                tracker,
                contextlib.aclosing(self._run_locked(session, message)) as events,
            ):
                async for event in events:
                    if event.type in {AgentEventType.DONE, AgentEventType.ERROR}:
                        terminal.append(event)
                    else:
                        if span is not None:
                            _record_span_event(collector, span, event)
                        yield event
            for event in terminal:
                if span is not None:
                    _record_span_event(collector, span, event)
                yield event
        except asyncio.CancelledError:
            from app.core.task_state_machine import TaskState

            with contextlib.suppress(Exception):
                if session.state_machine.can_transition_to(TaskState.CANCELLED):
                    await session.state_machine.transition(TaskState.CANCELLED, trigger="consumer_cancelled")
            raise
        except Exception as exc:
            span_status = "error"
            _record_audit(
                audit_chain,
                "agent_run_error",
                session_id=session.session_id,
                input_summary=message,
                output_summary=str(exc),
            )
            raise
        finally:
            if span is not None:
                try:
                    collector.end_span(span, status=span_status)
                except Exception as exc:
                    logger.warning(
                        "trace_span_end_failed",
                        session_id=session.session_id,
                        status=span_status,
                        error=str(exc),
                        error_type=type(exc).__name__,
                    )
            _record_audit(
                audit_chain,
                "agent_run_end",
                session_id=session.session_id,
                output_summary=span_status,
            )
            if self._session_locks.get(session.session_id) is lock:
                self._session_locks.pop(session.session_id, None)
    async def run_agent(self, session: AgentSession, message: str) -> dict[str, Any]:
        """Consume the streaming API and return the legacy aggregate result."""
        output_parts: list[str] = []
        tokens_used = 0
        status = None
        error = None
        cost_status = "unknown"
        async for event in self.run(session, message):
            if event.type == AgentEventType.TEXT:
                output_parts.append(event.data.get("content", ""))
            elif event.type == AgentEventType.DONE:
                tokens_used = event.data.get("tokens_used", tokens_used)
                status = event.data.get("status")
                cost_status = event.data.get("cost_status", "unknown")
                if not output_parts and event.data.get("content"):
                    output_parts.append(event.data["content"])
            elif event.type == AgentEventType.ERROR:
                error = event.data.get("error")
        return {"output": "".join(output_parts),
                "tokens_used": getattr(session, "_run_tokens", tokens_used),
                "status": status or session.status.value, "error": error,
                "cost_status": cost_status,
                "usage_status": getattr(session, "_run_usage_status", "unknown")}

    async def _run_locked(self, session: AgentSession, message: str) -> AsyncIterator[AgentEvent]:
        """Internal run method - executes under session lock."""
        current = session.state_machine.state
        from app.core.task_state_machine import TaskState
        if current in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
            await session.state_machine.transition(TaskState.PENDING, trigger="user_restart")
        await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")
        # A recovered session already carries the restored transcript, the turn
        # it belongs to and its iteration count. Appending the caller's text
        # again would fork the history the checkpoint preserved and burn an
        # iteration the recovered run had already spent, so the resumed run
        # continues that turn instead of starting a parallel one.
        resuming = session._resume_interrupted
        if not resuming:
            session._stop_requested = False
            session.messages.append({"role": MessageRole.USER, "content": message})
            await persist_message(session.session_id, MessageRole.USER, content=message)

        self._set_agent_mode(session)
        self._set_memory_scope(session)
        self._send_start_notification(session)
        if not resuming:
            await self._inject_memory_context(session, message)
            await self._inject_core_memory(session)
        await self._inject_lessons(session, message)
        await self._inject_graph_context(session)

        session._last_result = None
        if not resuming:
            session._last_iteration = 0
        session._run_status_override = None
        session._last_assistant_message_id = None
        executor = ParallelToolExecutor(
            self.tool_registry,
            validator=(lambda name, args: validate_tool_call(session, name, args, self.sandbox, self.permission_overlay, self.agent_mode, self.tool_registry)),
            session=session,
            max_result_chars=getattr(self, "_tool_result_char_limit", DEFAULT_MAX_RESULT_CHARS),
        )
        compressor = ContextCompressor(session.context_config)
        result: ChatResult | None = None

        try:
            # The same aclosing() contract as run(): an early GeneratorExit has
            # to reach the iteration loop so a half-consumed stream still records
            # what the model reported before the turn is committed.
            async with contextlib.aclosing(self._iteration_loop(session, executor, compressor)) as events:
                async for event in events:
                    yield event
        except Exception as e:
            # A run whose turn could not be made durable has produced no
            # recoverable state, so it is reported as an error and re-raised:
            # a checkpoint store that cannot be written is an operator problem,
            # not an agent failure the caller should absorb as a failed turn.
            session._last_error = str(e)
            if isinstance(e, _CheckpointUnavailable):
                self._send_failure_notification(session, str(e))
                raise
            if session._stop_requested:
                await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
            elif session.state_machine.can_transition_to(TaskState.FAILED):
                await session.state_machine.transition(TaskState.FAILED, trigger="unhandled_error")
            # A turn that had already reached a terminal state stays there: the
            # turn row is committed from the state machine, so downgrading
            # COMPLETED back to FAILED would be a second, contradictory record
            # of the same run.
            yield AgentEvent(type=AgentEventType.ERROR, data={"error": str(e)})
            self._send_failure_notification(session, str(e))
            return

        if session.status.value == "failed" and session._run_status_override is None:
            return

        await self._store_episodic_memory(session, message)
        self._trigger_memory_reflection(session)
        result = session._last_result
        yield AgentEvent(type=AgentEventType.DONE, data={
            "status": session._run_status_override or session.status.value,
            "iterations": session._last_iteration,
            "content": result.content if result else "",
            "tokens_used": getattr(session, "_run_tokens", 0),
            "cost_status": getattr(session, "_run_cost_status", "unknown"),
            "usage_status": getattr(session, "_run_usage_status", "unknown"),
            "metrics": session.metrics.to_dict(),
            "message_id": getattr(session, "_last_assistant_message_id", None),
        })

    async def _iteration_loop(
        self,
        session: AgentSession,
        executor: Any,
        compressor: Any,
    ) -> AsyncIterator[AgentEvent]:
        """Main iteration loop for agent execution."""
        from app.core.task_state_machine import TaskState

        # A recovered turn already spent the iterations the checkpoint
        # recorded; restarting the count would hand it a fresh budget it never
        # had. The flag is consumed here so downstream bookkeeping sees a
        # normal run.
        iteration = session._last_iteration if session._resume_interrupted else 0
        session._resume_interrupted = False
        run_store = getattr(self, "_run_store", None)
        adapter = self.model_registry.get_or_create(
            provider=session.provider,
            model_id=session.model_id,
            api_key=session.api_key,
            base_url=session.base_url,
        )
        tools = build_tools(
            self.tool_registry,
            session.tools,
            self.tool_prioritizer,
            task_description=session.messages[-1].get("content", "") if session.messages else "",
            max_tools=self._prompt_tool_budget(session),
        )
        result: ChatResult | None = None

        while iteration < session.max_iterations and not session._stop_requested:
            iteration += 1
            session._last_iteration = iteration
            session.metrics.total_iterations += 1
            yield AgentEvent(type=AgentEventType.THINKING, data={"iteration": iteration})

            ctx_tokens = estimate_tokens(session.messages)
            ctx_limit = getattr(adapter.capabilities, "max_tokens", None) or session.context_config.max_tokens
            if compressor.needs_compression(session.messages) or (ctx_limit and ctx_tokens > ctx_limit * 0.8):
                session.messages = await compressor.compress(session.messages, adapter)
                yield AgentEvent(type=AgentEventType.CONTEXT_COMPRESSION, data={"iteration": iteration, "tokens": ctx_tokens, "limit": ctx_limit})

            if adapter.capabilities.streaming:
                result = ChatResult()
                started = time.monotonic()
                try:
                    async for chunk in adapter.stream_chat(messages=session.messages, tools=tools or None):
                        # One accumulator decides what a chunk means: an
                        # authoritative cumulative snapshot is trusted and only
                        # its unseen suffix is emitted, a plain delta is
                        # appended. Re-implementing that here re-appended the
                        # snapshot on every chunk, and chunk.usage (a dict) was
                        # written straight into the integer token field.
                        delta = merge_stream_chunk(result, chunk)
                        if session._stop_requested:
                            if run_store is not None:
                                await run_store.record_response(session, result, iteration, complete=False)
                            session.metrics.total_tokens_used += getattr(result, "tokens_used", 0) or 0
                            result = None
                            break
                        if delta:
                            yield AgentEvent(type=AgentEventType.TEXT, data={"content": delta})
                        self._accumulate_stream_tool_calls(result.tool_calls, chunk.tool_calls)
                except BaseException:
                    if result is not None:
                        if run_store is not None:
                            await run_store.record_response(session, result, iteration, complete=False)
                        session.metrics.total_tokens_used += getattr(result, "tokens_used", 0) or 0
                    raise
                finally:
                    session.metrics.llm_call_durations.append(time.monotonic() - started)
                if result is not None:
                    result.finish_reason = result.finish_reason or ("tool_calls" if result.tool_calls else "stop")
            else:
                result = await self._call_llm_with_resilience(session, adapter, session.messages, iteration)
            if result is None:
                session._last_error = "LLM call failed or stopped"
                await session.state_machine.transition(
                    TaskState.CANCELLED if session._stop_requested else TaskState.FAILED,
                    trigger="llm_stopped")
                yield AgentEvent(type=AgentEventType.ERROR, data={"error": "LLM call failed or stopped"})
                break
            session._last_result = result
            # Normalize before bookkeeping so the store, the run totals and the
            # persisted message all read the same model-reported counters.
            result.tokens_used = response_usage(result)["total_tokens"] or 0
            if run_store is not None:
                await run_store.record_response(session, result, iteration, complete=result.finish_reason != "error")
            session.metrics.total_tokens_used += getattr(result, "tokens_used", 0) or 0
            if result.finish_reason == "error":
                raise RuntimeError("Model reported an error response")

            if result.content:
                async for event in self._handle_text_result(session, result, adapter):
                    yield event

            if not result.tool_calls and not result.content:
                session.messages.append({
                    "role": MessageRole.SYSTEM,
                    "content": "Your previous response was empty. Please provide a helpful response or use an appropriate tool.",
                })
                continue

            if result.tool_calls:
                async for _event in self._handle_tool_execution(session, executor, result, iteration, ctx_tokens):
                    yield _event
                continue

            break

        if session.status.value == "failed":
            return
        # A stop requested between the final model response and this point
        # would otherwise be reported as a completed turn whose checkpoint
        # claims "processing" -- a lie recovery then believes.
        if session._stop_requested and result is not None:
            if run_store is not None:
                await run_store.record_response(session, result, iteration, complete=False)
            session.metrics.total_tokens_used += getattr(result, "tokens_used", 0) or 0
        # Running out of iterations is only a success when the last round
        # actually answered. A budget that expired on an empty reply, on tool
        # calls still in flight, or before any model call landed produced
        # nothing, and reporting "completed" turned a broken turn into a
        # silent success.
        exhausted = result is None or result.tool_calls or not result.content
        if not session._stop_requested and iteration >= session.max_iterations and exhausted:
            await session.state_machine.transition(TaskState.FAILED, trigger="max_iterations")
            session._run_status_override = "max_iterations_reached"
            session._last_error = "Maximum iterations reached"
            await self._write_final_checkpoint(session, result, iteration)
            return

        if session._stop_requested:
            await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
        else:
            await session.state_machine.transition(TaskState.COMPLETED, trigger="run_complete")
            self._send_completion_notification(session, result)
        # Written after the terminal transition, so the snapshot states the
        # outcome: a checkpoint still reading "processing" makes recovery treat
        # a finished turn as an interrupted one, and turn.checkpoint_id would
        # point at a snapshot that no longer described reality.
        await self._write_final_checkpoint(session, result, iteration)
        yield AgentEvent(type=AgentEventType.CHECKPOINT, data={"iteration": iteration, "final": True})

    async def _write_final_checkpoint(self, session: AgentSession, result: Any, iteration: int) -> None:
        """Persist the turn's terminal checkpoint, failing the run if it cannot be written.

        Raises:
            _CheckpointUnavailable: Wrapping whatever the store raised. A
                checkpoint is a promise about what recovery will find; when the
                store is down that promise is broken, and the turn must not be
                reported as successful. The wrapper keeps the cause's class
                (RuntimeError, OSError, ...) intact for callers that inspect it.
        """
        try:
            await self._save_checkpoint(
                session,
                {"final_result": result.content if result is not None and result.content else ""},
            )
        except Exception as exc:
            session._last_error = str(exc)
            raise _CheckpointUnavailable(str(exc)) from exc

    async def _call_llm(self, adapter: Any, session: AgentSession, tools: list) -> ChatResult | None:
        """Call the LLM adapter and return the result.

        Args:
            adapter: The LLM adapter.
            session: The current session.
            tools: Available tool definitions.

        Returns:
            ChatResult or None if stopped.
        """
        from app.core.task_state_machine import TaskState

        if session._stop_requested:
            await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
            return None
        result = await adapter.chat(messages=session.messages, tools=tools or None)
        _record_usage(result, adapter, session)
        return result

    async def _call_llm_with_resilience(
        self,
        session: AgentSession,
        model_adapter: Any,
        messages: list[dict[str, Any]],
        iteration: int,
    ) -> ChatResult:
        """Call the LLM through the retry handler and circuit breaker.

        Args:
            session: The current session.
            model_adapter: The LLM adapter.
            messages: The messages to send.
            iteration: The current iteration number.

        Returns:
            The ChatResult from the model.

        Raises:
            RetryExhaustedError: If the call fails after retries are exhausted.
            CircuitBreakerOpenError: If the circuit breaker is open.
        """
        config = session.session_config
        timeout_config = config.timeouts or TimeoutConfig()
        circuit_config = config.circuit_breaker or CircuitBreakerConfig()
        breaker = session._circuit_breaker or CircuitBreaker(
            name=f"session-{session.session_id or 'default'}",
            config=circuit_config,
        )
        session._circuit_breaker = breaker

        tools = build_tools(
            self.tool_registry,
            session.tools,
            self.tool_prioritizer,
            task_description=(session.messages[-1].get("content", "") if session.messages else ""),
            max_tools=self._prompt_tool_budget(session),
        )

        start = time.monotonic()
        try:
            async def _single() -> ChatResult:
                if model_adapter.capabilities and getattr(model_adapter.capabilities, "streaming", False):
                    return await self._stream_accumulate(model_adapter, messages or session.messages, tools)
                return await model_adapter.chat(messages=messages or session.messages, tools=tools or None)

            async def _attempt() -> ChatResult:
                return await asyncio.wait_for(_single(), timeout=timeout_config.per_call_seconds)

            try:
                return await breaker.call(_attempt)
            except CircuitBreakerOpenError:
                raise
            except RetryExhaustedError:
                raise
            except TimeoutError:
                session.metrics.retry_count += 1
                raise RetryExhaustedError("LLM call timed out") from None
            except Exception as e:
                raise e
        finally:
            session.metrics.llm_call_durations.append(time.monotonic() - start)

    async def _stream_accumulate(self, adapter: Any, messages: list[dict[str, Any]], tools: list) -> ChatResult:
        """Accumulate a streaming response into a single ChatResult.

        Delegates to the same snapshot rules the streaming path uses, so a
        resilience-wrapped call and a direct one can never disagree about the
        content or the token counters they report.
        """
        result = ChatResult()
        async for chunk in adapter.stream_chat(messages=messages, tools=tools or None):
            merge_stream_chunk(result, chunk)
            if getattr(chunk, "tool_calls", None):
                self._accumulate_stream_tool_calls(result.tool_calls, chunk.tool_calls)
        if result.finish_reason is None:
            result.finish_reason = "tool_calls" if result.tool_calls else "stop"
        return result

    async def _save_checkpoint(
        self,
        session: AgentSession,
        checkpoint: CheckpointData | dict[str, Any],
        checkpoint_id: str = "",
        *,
        pending_writes: list[dict[str, Any]] | None = None,
    ) -> str:
        """Persist a checkpoint under the session's current turn thread.

        ``checkpoint`` is either a fully built ``CheckpointData`` (for callers
        that own the tool-result payload themselves) or a mapping of channel
        values, in which case the session-owned state (messages, iteration,
        status, turn thread, last error) is stamped here so every checkpoint
        describes the same session uniformly.

        Every payload is redacted before it reaches the store. The stores
        sanitize credential-shaped *fields* but know nothing about the session's
        API key, so a model echoing that key back inside a message would persist
        it verbatim; passing the key as a secret is what stops that.

        Uses the thread namespace so checkpoints from distinct turns stay
        isolated, and links each new checkpoint to the previous one in the same
        session to build a rollback-capable parent chain. Falls back to a plain
        save when the store does not support thread/parent arguments.
        """
        if isinstance(checkpoint, CheckpointData):
            cp = checkpoint
        else:
            last_iteration = getattr(session, "_last_iteration", 0)
            cp = CheckpointData(
                session_id=session.session_id,
                messages=session.messages,
                iteration=last_iteration,
                status=self._checkpoint_status(session),
                channel_values=dict(checkpoint or {}),
                channel_versions={"messages": last_iteration},
                versions_seen={"node": {"messages": last_iteration}},
            )
        cp = replace(
            cp,
            metadata={
                **cp.metadata,
                "thread_id": getattr(session, "current_turn_id", "") or "",
                "error": getattr(session, "_last_error", None),
            },
            pending_writes=list(pending_writes or cp.pending_writes or []),
        )
        cp = sanitize_checkpoint(cp, secrets=(getattr(session, "api_key", "") or "",))
        thread_id = getattr(session, "current_turn_id", "") or ""
        previous = getattr(session, "_last_checkpoint_id", None)
        cid_or_uuid = checkpoint_id or str(uuid4())
        try:
            cid = await self._checkpoints.save(
                None,
                cp,
                thread_id=thread_id,
                checkpoint_id=cid_or_uuid,
                parent_id=previous,
            )
        except TypeError:
            cid = await self._checkpoints.save(None, cp, checkpoint_id=cid_or_uuid)
        with contextlib.suppress(AttributeError):
            session._last_checkpoint_id = cid
        return cid

    @staticmethod
    def _checkpoint_status(session: AgentSession) -> str:
        """Return the session's current state as a checkpoint status string."""
        state = getattr(getattr(session, "state_machine", None), "state", None)
        return str(getattr(state, "value", None) or "processing")

    def _validate_tool_call(self, session: AgentSession, tool_name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        """Validate a tool call using the engine's configured sandbox/mode.

        Returns:
            A tuple of (allowed, reason).
        """
        return validate_tool_call(
            session,
            tool_name,
            arguments,
            sandbox=getattr(self, "sandbox", None),
            permission_overlay=getattr(self, "permission_overlay", None),
            agent_mode=getattr(self, "agent_mode", None),
            tool_registry=self.tool_registry,
        )

    def _build_tools(self, tool_names: list[str]) -> list[dict[str, Any]]:
        """Build OpenAI-style tool definitions for the given tool names."""
        return build_tools(self.tool_registry, list(tool_names or []), self.tool_prioritizer)

    async def graceful_shutdown(self) -> None:
        """Gracefully shut down the engine and all tracked sessions."""
        self._shutdown_event.set()
        for session in list(self._sessions.values()):
            with contextlib.suppress(Exception):
                await session.graceful_shutdown()
        background_tasks = tuple(self._background_tasks)
        if background_tasks:
            await asyncio.gather(*background_tasks, return_exceptions=True)
            self._background_tasks.difference_update(background_tasks)
        await self.resource_tracker.cleanup()

    async def recover_session(self, session: AgentSession) -> bool:
        """Attempt to recover a session from a saved checkpoint.

        Returns:
            True if a checkpoint was found and loaded, False otherwise.

        Raises:
            ValueError: If the checkpoint still carries pending writes, because
                a tool side effect the checkpoint cannot vouch for would be
                replayed. That refusal is a safety decision, so it is raised
                rather than folded into a False that reads as "nothing to
                restore" and invites a blind retry.
        """
        from app.core.recovery import RecoveryManager

        return await RecoveryManager(self._checkpoints).restore_session(session)

    async def __aenter__(self) -> AgentEngine:
        """Enter the engine context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the engine context manager after draining owned work."""
        await self.graceful_shutdown()

    @staticmethod
    def _accumulate_stream_tool_calls(accumulated: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> None:
        """Merge streamed tool call deltas into complete tool calls.

        A provider either numbers its calls (multi-call streams send argument
        fragments under ``index``) or identifies them (``id`` on the opening
        fragment). Resolving on the index alone collapsed every id-less fragment
        into slot 0, so two distinct calls arrived merged into one with their
        arguments concatenated. Identity therefore wins over position, and
        position is only a fallback for fragments that carry neither.
        """
        for position, tool_call in enumerate(chunks):
            call_id = tool_call.get("id")
            existing = next((i for i, call in enumerate(accumulated)
                             if call_id and call.get("id") == call_id), None)
            if "index" in tool_call:
                index = tool_call["index"]
            elif existing is not None:
                index = existing
            elif call_id and position < len(accumulated) and accumulated[position].get("id"):
                index = len(accumulated)
            else:
                index = position
            while len(accumulated) <= index:
                accumulated.append({
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                })
            target = accumulated[index]
            if tool_call.get("id"):
                target["id"] = tool_call["id"]
            function = tool_call.get("function", {})
            if function.get("name"):
                target["function"]["name"] = function["name"]
            if function.get("arguments") is not None:
                arguments = function["arguments"]
                if isinstance(arguments, dict):
                    arguments = json.dumps(arguments, ensure_ascii=False)
                elif not isinstance(arguments, str):
                    arguments = str(arguments)
                if isinstance(function["arguments"], dict):
                    target["function"]["arguments"] = arguments
                else:
                    target["function"]["arguments"] += arguments

    async def _stream_chat(self, adapter: Any, session: AgentSession, tools: list) -> ChatResult | None:
        """Handle streaming chat response.

        Args:
            adapter: The LLM adapter.
            session: The current session.
            tools: Available tool definitions.

        Returns:
            ChatResult with accumulated content, or None if stopped.
        """
        from app.core import ChatResult

        result = ChatResult()
        async for chunk in adapter.stream_chat(messages=session.messages, tools=tools or None):
            if session._stop_requested:
                return None
            merge_stream_chunk(result, chunk)
            self._accumulate_stream_tool_calls(result.tool_calls, chunk.tool_calls)
        result.finish_reason = result.finish_reason or ("tool_calls" if result.tool_calls else "stop")
        return result

    async def _handle_text_result(self, session: AgentSession, result: Any, adapter: Any) -> AsyncIterator[AgentEvent]:
        """Handle text content from LLM response.

        Args:
            session: The current session.
            result: The ChatResult.
            adapter: The LLM adapter.

        Yields:
            TEXT events for non-streaming path.
        """
        from app.models.openai_adapter import OpenAIAdapter

        if not result.tool_calls and result.content:
            xml_tool_calls = OpenAIAdapter._parse_xml_tool_calls(result.content)
            if xml_tool_calls:
                result.tool_calls = xml_tool_calls
                cleaned = re.sub(r"<function([^>]+)>.*?</\1>", "", result.content, flags=re.DOTALL | re.IGNORECASE).strip()
                if not cleaned:
                    result.content = ""

        session.messages.append({"role": MessageRole.ASSISTANT, "content": result.content})
        persisted_id = await persist_message(session.session_id, MessageRole.ASSISTANT, content=result.content, tokens=getattr(result, "tokens_used", 0))
        if persisted_id:
            session._last_assistant_message_id = persisted_id
        if not (adapter.capabilities and adapter.capabilities.streaming):
            yield AgentEvent(type=AgentEventType.TEXT, data={"content": result.content})

    async def _handle_tool_execution(
        self,
        session: AgentSession,
        executor: Any,
        result: Any,
        iteration: int,
        ctx_tokens: int,
    ) -> AsyncIterator[AgentEvent]:
        """Handle tool execution from LLM response.

        Args:
            session: The current session.
            executor: The parallel tool executor.
            result: The ChatResult with tool calls.
            iteration: Current iteration number.
            ctx_tokens: Current context token count.

        Yields:
            TOOL_CALL, TOOL_RESULT, and CHECKPOINT events.

        Returns:
            bool indicating whether to continue the loop.
        """
        from app.middleware.metrics import TOOL_CALL_LATENCY, TOOL_CALL_TOTAL

        session.messages.append({"role": MessageRole.ASSISTANT, "content": "", "tool_calls": result.tool_calls})
        await persist_message(session.session_id, MessageRole.ASSISTANT, content="", tool_calls=result.tool_calls)
        for tc in result.tool_calls:
            function = tc.get("function", {})
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            tool_call_id = tc.get("id") or make_tool_call_id(
                session.session_id, iteration, len(session.messages)
            )
            allowed, reason = self._validate_tool_call(session, function.get("name", ""), arguments)
            event_data = {"id": tool_call_id, "name": function.get("name"), "arguments": arguments}
            if not allowed and isinstance(reason, dict) and reason.get("requires_approval"):
                event_data.update(reason)
                event_data["tool_call_id"] = tool_call_id
                event_data["timeout_seconds"] = self.permission_timeout_seconds
                session._pending_permission = {**event_data, "decision": None}
                session._permission_event = asyncio.Event()
                yield AgentEvent(type=AgentEventType.TOOL_CALL, data=event_data)
                decision = await self._wait_for_permission(session)
                if decision in {"allow", "allow_session", "allow_always"}:
                    approved = getattr(session, "_approved_tool_calls", None)
                    if approved is None:
                        approved = set()
                        session._approved_tool_calls = approved
                    approved.add(_approval_key(function.get("name", ""), arguments))
            else:
                yield AgentEvent(type=AgentEventType.TOOL_CALL, data=event_data)
        tool_results = await executor.execute_all(result.tool_calls)
        session.metrics.total_tool_calls += len(result.tool_calls)
        for tr in tool_results:
            # Tool volume and latency were the two numbers the tool dashboards
            # read, and nothing in the engine ever produced them.
            TOOL_CALL_TOTAL.labels(tool_name=tr.tool_name, status="success" if tr.success else "error").inc()
            TOOL_CALL_LATENCY.labels(tool_name=tr.tool_name).observe((tr.duration_ms or 0.0) / 1000.0)
            session.metrics.tool_call_durations.append(getattr(tr, "duration_ms", 0.0) or 0.0)
            self.tool_prioritizer.record_outcome(tr.tool_name, tr.success, tr.duration_ms)
            yield AgentEvent(
                type=AgentEventType.TOOL_RESULT,
                data={
                    "id": tr.tool_call_id,
                    "tool_name": tr.tool_name,
                    "result": tr.result,
                    "error": tr.error,
                },
            )
            await self._handle_tool_debug(session, tr)
            tool_content = tr.result
            if tr.error or not tr.success:
                error_text = tr.error or "Tool execution failed without an error message."
                tool_content = f"Tool execution failed: {error_text}"
                if tr.result:
                    tool_content += f"\n\nTool output:\n{tr.result}"
            session.messages.append({"role": MessageRole.TOOL, "content": tool_content, "tool_call_id": tr.tool_call_id or tr.tool_name})
            await persist_message(
                session.session_id,
                MessageRole.TOOL,
                content=tool_content,
                tool_name=tr.tool_name,
                tool_call_id=tr.tool_call_id,
            )

        cp = CheckpointData(
            session_id=session.session_id,
            messages=session.messages,
            iteration=iteration,
            status=session.state_machine.state.value,
            tool_results=[
                {
                    "tool": tr.tool_name,
                    "tool_call_id": tr.tool_call_id,
                    "result": tr.result,
                    "error": tr.error,
                    "success": tr.success,
                }
                for tr in tool_results
            ],
            channel_values={"last_tool_calls": result.tool_calls, "last_tool_results": [tr.result for tr in tool_results], "context_tokens": ctx_tokens},
            channel_versions={"messages": iteration, "tools": len(result.tool_calls)},
            versions_seen={"node": {"messages": iteration, "tools": len(result.tool_calls)}},
            # A tool call leaves side effects the transcript cannot vouch for:
            # the checkpoint is the only record that any existed at all. Leaving
            # it blank made an interrupted tool round look replay-safe, so
            # recovery happily re-ran writes the run had already performed.
            pending_writes=[
                {"channel": "tools", "value": tc, "write_id": tc.get("id", str(index)),
                 "status": "committed"}
                for index, tc in enumerate(result.tool_calls)
            ],
        )
        await self._save_checkpoint(session, cp, f"{session.session_id}-{iteration}")
        yield AgentEvent(type=AgentEventType.CHECKPOINT, data={"iteration": iteration, "tool_calls": len(result.tool_calls)})

    async def _handle_tool_debug(self, session: AgentSession, tr: Any) -> None:
        """Handle debug recovery for failed tool calls.

        Args:
            session: The current session.
            tr: The tool result to check for errors.
        """
        if self.debug_loop and tr.error:
            key = tr.tool_name
            attempts = session.debug_attempts.get(key, 0)
            if attempts < 3:
                session.debug_attempts[key] = attempts + 1
                fixed = await self.debug_loop.recover(
                    tool_name=tr.tool_name,
                    arguments=tr.arguments or {},
                    error_output=tr.error or tr.result,
                    retry_callback=lambda retry_tool, retry_args: self.tool_registry.execute(retry_tool, retry_args),
                )
                if fixed and fixed.success and fixed.output:
                    tr.error = ""
                    tr.result = truncate_tool_result(
                        fixed.output,
                        getattr(self, "_tool_result_char_limit", DEFAULT_MAX_RESULT_CHARS),
                    )
                    tr.success = True

    def _set_agent_mode(self, session: AgentSession) -> None:
        """Set the current agent mode for tool execution context.

        Args:
            session: The agent session.
        """
        try:
            from app.core.file_patch import set_current_agent_mode
            set_current_agent_mode(session.mode)
        except Exception as exc:
            logger.warning(
                "agent_mode_binding_failed",
                session_id=session.session_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    def _set_memory_scope(self, session: AgentSession) -> None:
        """Bind the session's (user_id, agent_id) memory scope for tools.

        Self-editing memory tools (core_memory_append / core_memory_replace)
        resolve their target user/agent from this server-side contextvar rather
        than from model-supplied arguments, so a prompt cannot redirect a write
        into another user's or agent's memory.
        """
        try:
            from app.core.memory_context import set_memory_scope
            set_memory_scope(session.user_id, session.agent_id or None)
        except Exception as exc:
            logger.warning(
                "memory_scope_binding_failed",
                session_id=session.session_id,
                user_id=session.user_id,
                agent_id=session.agent_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    def _send_start_notification(self, session: AgentSession) -> None:
        """Send notification when agent starts.

        Args:
            session: The agent session.
        """
        try:
            from app.services.notifications import notification_service
            self._spawn(notification_service.agent_message(session.agent_id or "Agent", "开始执行任务..."))
        except Exception as exc:
            # Notification delivery is a side channel; the agent run must
            # proceed even when the notification service is unavailable.
            logger.debug(
                "start_notification_failed",
                session_id=session.session_id,
                agent_id=session.agent_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    def _send_completion_notification(self, session: AgentSession, result: Any) -> None:
        """Send notification when agent completes.

        Args:
            session: The agent session.
            result: The final ChatResult.
        """
        try:
            from app.services.notifications import notification_service
            self._spawn(notification_service.task_complete(f"Agent {session.agent_id}", result.content[:100] if result and result.content else None))
        except Exception as exc:
            # Notification delivery is a side channel; the run result is already
            # persisted and the caller must still receive it.
            logger.debug(
                "completion_notification_failed",
                session_id=session.session_id,
                agent_id=session.agent_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    def _send_failure_notification(self, session: AgentSession, error: str) -> None:
        """Send notification when agent fails.

        Args:
            session: The agent session.
            error: The error message.
        """
        try:
            from app.services.notifications import notification_service
            self._spawn(notification_service.task_failed(f"Agent {session.agent_id}", error))
        except Exception as exc:
            # The failure itself is already reported by the caller's error path;
            # a failed notification must not mask it.
            logger.debug(
                "failure_notification_failed",
                session_id=session.session_id,
                agent_id=session.agent_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    def _spawn(self, coro: Any) -> None:
        """Run a fire-and-forget task while holding a reference until it finishes."""
        try:
            task = asyncio.create_task(coro)
            self._background_tasks.add(task)
            task.add_done_callback(self._background_task_done)
        except Exception as exc:
            # `create_task` needs a running loop; without one the coroutine can
            # only be closed. It is fire-and-forget, so dropping it is correct.
            logger.debug(
                "background_task_spawn_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )

    def _background_task_done(self, task: asyncio.Task) -> None:
        """Release a completed task and consume failures from fire-and-forget work."""
        self._background_tasks.discard(task)
        if task.cancelled():
            return
        with contextlib.suppress(Exception):
            task.exception()

    async def _inject_memory_context(self, session: AgentSession, message: str) -> None:
        """Inject relevant memories into session context.

        Args:
            session: The agent session.
            message: The user query for memory retrieval.
        """
        try:
            memory_context = await self.memory_service.format_memories_for_prompt(
                user_id=session.user_id,
                query=message,
                max_memories=5,
                agent_id=session.agent_id or None,
            )
            if memory_context:
                memory_marker = "<!-- MEMORY_CONTEXT -->"
                for i, msg in enumerate(session.messages):
                    if msg.get("content", "").startswith(memory_marker):
                        session.messages[i] = {"role": MessageRole.SYSTEM, "content": memory_marker + "\n" + memory_context}
                        break
                else:
                    session.messages.insert(-1, {"role": MessageRole.SYSTEM, "content": memory_marker + "\n" + memory_context})
        except Exception as exc:
            # Memory injection only enriches the prompt; a retrieval failure
            # leaves the session usable with no memory context.
            logger.debug(
                "memory_context_injection_failed",
                session_id=session.session_id,
                user_id=session.user_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    async def _inject_core_memory(self, session: AgentSession) -> None:
        """Inject core memory blocks into session context.

        Args:
            session: The agent session.
        """
        try:
            from app.core.core_memory import core_memory
            blocks = await core_memory.get_blocks(user_id=session.user_id, agent_id=session.agent_id)
            if blocks:
                core_memory_xml = core_memory.format_for_prompt(blocks)
                core_marker = "<!-- CORE_MEMORY -->"
                for i, msg in enumerate(session.messages):
                    if msg.get("content", "").startswith(core_marker):
                        session.messages[i] = {"role": MessageRole.SYSTEM, "content": core_marker + "\n" + core_memory_xml}
                        break
                else:
                    session.messages.insert(-1, {"role": MessageRole.SYSTEM, "content": core_marker + "\n" + core_memory_xml})
        except Exception as exc:
            # Core memory is optional prompt enrichment; the run continues
            # without it when the blocks cannot be read.
            logger.debug(
                "core_memory_injection_failed",
                session_id=session.session_id,
                user_id=session.user_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    async def _inject_lessons(self, session: AgentSession, message: str) -> None:
        """Inject keyword-matched lessons (gptme-style) as a SYSTEM message.

        Lessons are episodic memories with ``memory_type="lesson"`` recorded via
        the ``save_lesson`` tool. They are injected only when the current user
        message retrieves at least one hit (keyword/vector match), so quiet
        sessions carry no extra prompt surface. The injection replaces the
        previous lessons marker rather than accumulating.
        """
        try:
            if not message or not message.strip():
                return
            lessons = await self.memory_service.retrieve_memories(
                user_id=session.user_id,
                query=message,
                limit=3,
                agent_id=session.agent_id or None,
                memory_type="lesson",
            )
            if not lessons:
                return
            lines = ["Relevant lessons from past work (apply them proactively):"]
            lines.extend(f"- {mem.summary or mem.content}" for mem in lessons)
            lessons_text = "\n".join(lines)
            lessons_marker = LESSONS_MARKER
            for i, msg in enumerate(session.messages):
                if msg.get("content", "").startswith(lessons_marker):
                    session.messages[i] = {"role": MessageRole.SYSTEM, "content": lessons_marker + "\n" + lessons_text}
                    break
            else:
                session.messages.insert(-1, {"role": MessageRole.SYSTEM, "content": lessons_marker + "\n" + lessons_text})
        except Exception as exc:
            # Lesson recall is best-effort context; retrieval errors must not
            # block the turn that triggered them.
            logger.debug(
                "lesson_injection_failed",
                session_id=session.session_id,
                user_id=session.user_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    async def _inject_graph_context(self, session: AgentSession) -> None:
        """Inject the agent's graph context as a SYSTEM message (opt-in only).

        Returns an empty string for agents that did not enable graph memory, so
        the disabled path costs nothing. Replaces the previous marker rather
        than accumulating, matching the memory/core-memory/lessons injections.
        """
        try:
            settings = await self.memory_service.get_graph_memory_settings(
                session.agent_id or None
            )
            graph_context = await self.memory_service.format_graph_context_for_prompt(
                user_id=session.user_id,
                agent_id=session.agent_id or None,
                memory_config=settings,
            )
            if not graph_context:
                return
            marker = GRAPH_CONTEXT_MARKER
            for i, msg in enumerate(session.messages):
                if msg.get("content", "").startswith(marker):
                    session.messages[i] = {"role": MessageRole.SYSTEM, "content": marker + "\n" + graph_context}
                    break
            else:
                session.messages.insert(-1, {"role": MessageRole.SYSTEM, "content": marker + "\n" + graph_context})
        except Exception as exc:
            # Graph memory is opt-in context; when it cannot be read the agent
            # simply runs without the graph section.
            logger.debug(
                "graph_context_injection_failed",
                session_id=session.session_id,
                user_id=session.user_id,
                agent_id=session.agent_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    async def _store_episodic_memory(self, session: AgentSession, message: str) -> None:
        """Store important interaction in episodic memory.

        Also feeds the opt-in graph memory, which is a no-op (no DB work)
        unless the agent enabled it in its ``memory_config``.

        Args:
            session: The agent session.
            message: The user message.
        """
        try:
            result = getattr(session, "_last_result", None)
            if result and result.content and len(result.content) > 10:
                content = f"User: {message}\nAssistant: {result.content[:500]}"
                await self.memory_service.create_episodic_memory(
                    user_id=session.user_id,
                    content=content,
                    agent_id=session.agent_id,
                    source_session_id=session.session_id,
                    importance=0.7,
                )
                settings = await self.memory_service.get_graph_memory_settings(
                    session.agent_id or None
                )
                self._spawn(
                    self.memory_service.record_graph_memory(
                        user_id=session.user_id,
                        content=content,
                        memory_config=settings,
                        agent_id=session.agent_id or None,
                    )
                )
        except Exception as exc:
            # Episodic and graph memory are post-turn bookkeeping; the
            # assistant response is already delivered to the caller.
            logger.debug(
                "episodic_memory_store_failed",
                session_id=session.session_id,
                user_id=session.user_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    def _trigger_memory_reflection(self, session: AgentSession) -> None:
        """Trigger memory reflection (fire-and-forget).

        Args:
            session: The agent session.
        """
        try:
            from app.core.memory_reflection import memory_reflection
            self._spawn(memory_reflection.maybe_reflect(session.user_id))
        except Exception as exc:
            # Reflection is opportunistic; a failure must not surface to the
            # user who just finished a turn.
            logger.debug(
                "memory_reflection_trigger_failed",
                session_id=session.session_id,
                user_id=session.user_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    async def _wait_for_permission(self, session: AgentSession) -> str:
        """Wait for a permission decision and always clear its live wait state."""
        pending = session._pending_permission
        event = session._permission_event
        if pending is None or event is None:
            return "deny"

        try:
            await asyncio.wait_for(event.wait(), timeout=self.permission_timeout_seconds)
        except TimeoutError:
            if session._pending_permission is pending:
                pending["decision"] = "timeout"
        finally:
            decision = pending.get("decision") or "deny"
            if session._pending_permission is pending:
                session._pending_permission = None
                if session._permission_event is event:
                    session._permission_event = None
        return decision

    def resolve_permission(self, tool_call_id: str, decision: str, user_id: str | None = None) -> bool:
        """Resolve a pending permission request.

        Args:
            tool_call_id: The ID of the tool call awaiting permission.
            decision: One of 'allow', 'allow_session', 'allow_always', 'deny'.

        Returns:
            True if the permission was resolved, False if no pending request found.
        """
        for session in self._sessions.values():
            if session._pending_permission and session._pending_permission.get("tool_call_id") == tool_call_id:
                if user_id is not None and str(session.user_id) != str(user_id):
                    continue
                session._pending_permission["decision"] = decision
                if session._permission_event is not None:
                    session._permission_event.set()
                return True
        return False

    def has_pending_permission(self, tool_call_id: str) -> bool:
        """Return whether any live session owns a pending approval."""
        return any(
            session._pending_permission
            and session._pending_permission.get("tool_call_id") == tool_call_id
            for session in self._sessions.values()
        )

    def close_session(self, session_id: str) -> bool:
        """Release an in-memory session and everything it holds.

        Sessions were previously only ever added to ``self._sessions``, so
        every session created for the process lifetime stayed resident --
        messages, tool results, and ``session_config.api_key`` -- with no
        release path. ``DELETE /api/v1/sessions/{id}`` removed the database
        row only, which made the leak invisible to callers.

        Args:
            session_id: Identifier of the session to close.

        Returns:
            True if a session was found and released, False if unknown.
        """
        session = self._sessions.pop(session_id, None)
        lock = self._session_locks.get(session_id)
        if lock is None or not lock.locked():
            self._session_locks.pop(session_id, None)
        order = getattr(self, "_session_order", None)
        if order is not None and session_id in order:
            order.remove(session_id)
        if session is None:
            return False

        # A run() holding the session keeps its own reference, so removing
        # the registry entry is not enough: ask the loop to wind down and
        # release the credential held on the config object.
        with contextlib.suppress(Exception):
            session.stop()
        with contextlib.suppress(Exception):
            session.session_config.api_key = ""

        # Unblock any coroutine parked in the approval wait; it observes the
        # cleared pending record on resume and proceeds without approval.
        if session._pending_permission is not None:
            session._pending_permission["decision"] = "deny"
            if session._permission_event is not None:
                with contextlib.suppress(RuntimeError):
                    session._permission_event.set()
        session._pending_permission = None
        session._permission_event = None
        with contextlib.suppress(Exception):
            session._pending_tasks.clear()
        return True

    def get_permission_config(self) -> Any:
        """Get the default permission configuration.

        Returns:
            The default PermissionConfig instance.
        """
        return self._default_permission_config

    def update_permission_config(self, config: Any) -> None:
        """Update the default permission configuration for new and existing sessions, and persist it.

        Args:
            config: The new permission configuration.
        """
        self._default_permission_config = config
        for session in list(self._sessions.values()):
            with contextlib.suppress(Exception):
                session.permission_config = config
        self._save_permission_config(config)
