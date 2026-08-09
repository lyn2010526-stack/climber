"""Agent session management for the agent engine."""

from __future__ import annotations

import asyncio
import copy
import time
from dataclasses import asdict, dataclass
from typing import Any

from app.core import (
    CheckpointData,
    ContextConfig,
    SessionStatus,
)
from app.core.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    IterationTimeoutError,
    RetryConfig,
    SessionMetrics,
    SessionTimeoutError,
    TimeoutConfig,
)
from app.core.task_state_machine import TaskState, TaskStateMachine

_SENTINEL = object()


@dataclass
class SessionConfig:
    """Configuration for an agent session.

    Encapsulates all session parameters to avoid excessive function arguments.
    All identity fields default to empty strings so partial configs are valid.
    """
    session_id: str = ""
    agent_id: str = ""
    user_id: str = ""
    provider: str = ""
    model_id: str = ""
    api_key: str = ""
    base_url: str | None = None
    system_prompt: str = ""
    tools: list[str] | None = None
    context_config: ContextConfig | None = None
    mode: str = "act"
    max_iterations: int = 10
    retry: RetryConfig | None = None
    timeouts: TimeoutConfig | None = None
    circuit_breaker: CircuitBreakerConfig | None = None
    enable_checkpoint_recovery: bool = False
    enable_graceful_shutdown: bool = False
    shutdown_drain_seconds: float = 0.0


class AgentSession:
    """Represents a single agent interaction session with state management."""

    def __init__(
        self,
        config: SessionConfig | None = None,
        *,
        session_id: Any = _SENTINEL,
        agent_id: Any = _SENTINEL,
        user_id: Any = _SENTINEL,
        provider: Any = _SENTINEL,
        model_id: Any = _SENTINEL,
        api_key: Any = _SENTINEL,
        base_url: Any = _SENTINEL,
        system_prompt: Any = _SENTINEL,
        tools: Any = _SENTINEL,
        context_config: Any = _SENTINEL,
        mode: Any = _SENTINEL,
        max_iterations: Any = _SENTINEL,
        session_config: SessionConfig | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an agent session.

        Supports either a single SessionConfig positional argument or explicit
        keyword arguments (optionally combined with a session_config override).
        """
        base = config if config is not None else (session_config if session_config is not None else SessionConfig())
        overrides = {
            "session_id": session_id,
            "agent_id": agent_id,
            "user_id": user_id,
            "provider": provider,
            "model_id": model_id,
            "api_key": api_key,
            "base_url": base_url,
            "system_prompt": system_prompt,
            "tools": tools,
            "context_config": context_config,
            "mode": mode,
            "max_iterations": max_iterations,
        }
        for name, value in overrides.items():
            if value is not _SENTINEL:
                setattr(base, name, value)

        self.session_config = base
        self.session_id = base.session_id
        self.agent_id = base.agent_id
        self.user_id = base.user_id
        self.provider = base.provider
        self.model_id = base.model_id
        self.api_key = base.api_key
        self.base_url = base.base_url
        self.system_prompt = base.system_prompt
        self.tools = base.tools or []
        self.context_config = base.context_config or ContextConfig()
        self.max_iterations = base.max_iterations
        self.mode = base.mode
        self.context: dict[str, Any] = context or {}
        self.messages: list[dict[str, Any]] = []
        self._stop_requested = False
        self._last_iteration = 0
        self._last_error: str | None = None
        self._resume_interrupted = False
        self.tool_results: list[dict[str, Any]] = []
        self.session_memory = _SessionMemory(self)
        self.current_turn_id: str | None = None
        self.state_machine = TaskStateMachine(task_id=self.session_id or "session", initial_state=TaskState.PENDING)
        self.debug_attempts: dict[str, int] = {}
        self.restart_count: int = 0
        self.paused_at: str | None = None
        self.termination_reason: str | None = None
        self._init_permission_system()
        self._pending_permission: dict[str, Any] | None = None
        self._permission_event: asyncio.Event | None = None
        self._pending_tasks: set[asyncio.Task] = set()
        self.metrics = SessionMetrics(session_id=self.session_id or "session")
        self._session_deadline: float | None = None
        self._iteration_deadline: float | None = None
        self._circuit_breaker: CircuitBreaker | None = None

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot without runtime primitives or secrets."""
        config = asdict(self.session_config)
        config.pop("api_key", None)
        config["context_config"] = asdict(self.context_config)
        return {
            "config": config,
            "context": copy.deepcopy(self.context),
            "messages": copy.deepcopy(self.messages),
            "status": self.state_machine.state.value,
            "iteration": self._last_iteration,
            "stop_requested": self._stop_requested,
            "error": self._last_error,
            "tool_results": copy.deepcopy(self.tool_results),
            "current_turn_id": self.current_turn_id,
            "restart_count": self.restart_count,
            "paused_at": self.paused_at,
            "termination_reason": self.termination_reason,
            "resume_interrupted": self._resume_interrupted,
        }

    @classmethod
    def from_snapshot(
        cls,
        snapshot: dict[str, Any],
        *,
        api_key: str = "",
    ) -> AgentSession:
        """Rebuild a session from a persisted snapshot with safe defaults."""
        raw_config = snapshot.get("config")
        config_data = dict(raw_config) if isinstance(raw_config, dict) else {}
        raw_context_config = config_data.pop("context_config", None)
        if isinstance(raw_context_config, dict):
            context_config = ContextConfig(**raw_context_config)
        else:
            context_config = ContextConfig()
        config_data["context_config"] = context_config
        nested_configs = {
            "retry": RetryConfig,
            "timeouts": TimeoutConfig,
            "circuit_breaker": CircuitBreakerConfig,
        }
        for name, config_type in nested_configs.items():
            value = config_data.get(name)
            if isinstance(value, dict):
                config_data[name] = config_type(**value)
        config_data["api_key"] = api_key
        allowed_config_fields = SessionConfig.__dataclass_fields__
        config = SessionConfig(
            **{
                key: value
                for key, value in config_data.items()
                if key in allowed_config_fields
            }
        )
        raw_context = snapshot.get("context")
        session = cls(
            config,
            context=copy.deepcopy(raw_context) if isinstance(raw_context, dict) else {},
        )
        raw_messages = snapshot.get("messages")
        session.messages = (
            copy.deepcopy(raw_messages) if isinstance(raw_messages, list) else []
        )
        raw_tool_results = snapshot.get("tool_results")
        session.tool_results = (
            copy.deepcopy(raw_tool_results) if isinstance(raw_tool_results, list) else []
        )
        session._last_iteration = max(0, int(snapshot.get("iteration", 0) or 0))
        session._stop_requested = bool(snapshot.get("stop_requested", False))
        error = snapshot.get("error")
        session._last_error = str(error) if error is not None else None
        session.current_turn_id = snapshot.get("current_turn_id") or None
        session.restart_count = max(0, int(snapshot.get("restart_count", 0) or 0))
        session.paused_at = snapshot.get("paused_at") or None
        session.termination_reason = snapshot.get("termination_reason") or None
        session._resume_interrupted = bool(snapshot.get("resume_interrupted", False))
        session._restore_status(snapshot.get("status", TaskState.PENDING.value))
        return session

    def restore_checkpoint(
        self,
        checkpoint: CheckpointData,
        *,
        interrupted: bool,
    ) -> None:
        """Apply checkpoint execution state to this session."""
        self.messages = copy.deepcopy(checkpoint.messages)
        tool_results = checkpoint.tool_results
        if not tool_results:
            channel_tool_results = checkpoint.channel_values.get("last_tool_results", [])
            tool_results = (
                copy.deepcopy(channel_tool_results)
                if isinstance(channel_tool_results, list)
                else []
            )
        self.tool_results = copy.deepcopy(tool_results)
        self._last_iteration = max(0, checkpoint.iteration)
        self._last_error = checkpoint.metadata.get("error")
        self.current_turn_id = checkpoint.metadata.get("thread_id") or None
        self._resume_interrupted = interrupted
        self._stop_requested = False
        status = checkpoint.status if interrupted else TaskState.COMPLETED.value
        self._restore_status(status)

    def _restore_status(self, status: Any) -> None:
        state_by_status = {
            "running": TaskState.PROCESSING,
            "stopped": TaskState.CANCELLED,
        }
        status_value = str(status)
        try:
            state = state_by_status.get(status_value)
            if state is None:
                state = TaskState(status_value)
        except ValueError:
            state = TaskState.PENDING
        self.state_machine._state = state
        self.state_machine._metadata["state"] = state.value

    def _init_permission_system(self) -> None:
        """Initialize the permission system for this session."""
        try:
            from app.core.permission_rules import get_default_config
            self.permission_config = get_default_config()
        except Exception:
            self.permission_config = None

    @property
    def status(self) -> SessionStatus:
        """Map TaskState to legacy SessionStatus for backward compatibility.

        Returns:
            The current session status.
        """
        mapping = {
            TaskState.PENDING: SessionStatus.PENDING,
            TaskState.PROCESSING: SessionStatus.RUNNING,
            TaskState.PAUSED: SessionStatus.PAUSED,
            TaskState.COMPLETED: SessionStatus.COMPLETED,
            TaskState.FAILED: SessionStatus.FAILED,
            TaskState.CANCELLED: SessionStatus.STOPPED,
        }
        return mapping.get(self.state_machine.state, SessionStatus.PENDING)

    @property
    def remaining_session_seconds(self) -> float:
        """Seconds remaining before the session deadline."""
        if self._session_deadline is not None:
            return max(0.0, self._session_deadline - time.monotonic())
        return self.session_config.timeouts.per_session_seconds if self.session_config.timeouts else 1800.0

    def stop(self) -> None:
        """Request the session to stop processing."""
        self._stop_requested = True
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.state_machine.transition(TaskState.CANCELLED, trigger="user_stop"))
        except RuntimeError:
            pass

    async def pause(self) -> None:
        """Pause the session, recording the pause timestamp."""
        if self.state_machine.state == TaskState.PENDING:
            await self.state_machine.transition(TaskState.PROCESSING, trigger="auto_start")
        await self.state_machine.transition(TaskState.PAUSED, trigger="user_pause")
        self.paused_at = __import__("datetime").datetime.utcnow().isoformat()

    async def resume(self) -> None:
        """Resume from PAUSED back to PROCESSING."""
        await self.state_machine.transition(TaskState.PROCESSING, trigger="user_resume")
        self.paused_at = None

    async def terminate(self, reason: str = "user_terminate") -> None:
        """Terminate the session with a reason."""
        await self.state_machine.transition(TaskState.CANCELLED, trigger=reason)
        self.termination_reason = reason

    async def restart(self) -> None:
        """Reset session to PENDING for re-execution."""
        await self.state_machine.transition(TaskState.PENDING, trigger="user_restart")
        self.restart_count += 1
        self.termination_reason = None
        self.paused_at = None

    def _fire_and_forget(self, coro: Any) -> asyncio.Task:
        """Create a background task and track it for cleanup.

        Args:
            coro: The coroutine to run in background.

        Returns:
            The created asyncio Task.
        """
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)
        return task

    async def _await_pending_tasks(self) -> None:
        """Await all pending fire-and-forget tasks and clear the set."""
        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)
            self._pending_tasks.clear()

    def start_session_timer(self) -> None:
        """Start the overall session deadline timer."""
        timeout = self.session_config.timeouts.per_session_seconds if self.session_config.timeouts else 1800.0
        self._session_deadline = time.monotonic() + timeout

    def start_iteration_timer(self) -> None:
        """Start the per-iteration deadline timer."""
        timeout = self.session_config.timeouts.per_iteration_seconds if self.session_config.timeouts else 120.0
        self._iteration_deadline = time.monotonic() + timeout

    def check_timeouts(self) -> None:
        """Check active deadline timers and raise if exceeded.

        Raises:
            SessionTimeoutError: If the session deadline is exceeded.
            IterationTimeoutError: If the iteration deadline is exceeded.
        """
        now = time.monotonic()
        if self._session_deadline is not None and now > self._session_deadline:
            raise SessionTimeoutError(f"Session deadline exceeded for session '{self.session_id}'")
        if self._iteration_deadline is not None and now > self._iteration_deadline:
            raise IterationTimeoutError(f"Iteration deadline exceeded for session '{self.session_id}'")

    async def graceful_shutdown(self) -> None:
        """Gracefully stop the session, draining pending tasks and closing metrics."""
        self._stop_requested = True
        drain = self.session_config.shutdown_drain_seconds if self.session_config else 0.0
        if drain > 0:
            await asyncio.sleep(drain)
        await self._await_pending_tasks()
        if self.metrics.end_time is None:
            self.metrics.end_time = time.monotonic()

    async def __aenter__(self) -> AgentSession:
        """Enter the session context, starting the session timer."""
        self.start_session_timer()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the session context, requesting stop and closing metrics."""
        self._stop_requested = True
        if self.metrics.end_time is None:
            self.metrics.end_time = time.monotonic()


class _SessionMemory:
    """Simple message memory for an agent session."""

    def __init__(self, session: AgentSession) -> None:
        self._session = session

    def add(self, role: str, content: str) -> None:
        """Add a message to the session memory.

        Args:
            role: The message role (user/assistant/system/tool).
            content: The message content.
        """
        self._session.messages.append({"role": role, "content": content})
