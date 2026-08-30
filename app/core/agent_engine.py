"""Minimal agent engine with ReAct loop."""

from __future__ import annotations

import asyncio
import os
import re
import time
from collections.abc import AsyncIterator
from contextlib import nullcontext
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

import structlog

logger = structlog.get_logger()

_background_tasks: set[asyncio.Task] = set()
# Module-level singleton for main app lifecycle management
_main_engine: AgentEngine | None = None


def get_main_engine() -> AgentEngine | None:
    """Return the main AgentEngine singleton (set via set_main_engine)."""
    return _main_engine


def set_main_engine(engine: AgentEngine) -> None:
    """Register the main AgentEngine singleton for lifecycle management."""
    global _main_engine
    _main_engine = engine


def _spawn(coro: Any) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task

from app.core import (
    AgentEvent,
    AgentEventType,
    ChatResult,
    CheckpointData,
    ContextConfig,
    MessageRole,
    SessionStatus,
)
from app.core.checkpoint import InMemoryCheckpointStore
from app.core.compressor import ContextCompressor, estimate_tokens
from app.core.di import resolve as di_resolve
from app.core.event_replay import EventReplayBuffer, ReplayRecord
from app.core.integration.recorder import RECORDED_AGENT_EVENTS, attach_session_recorder, record
from app.core.middleware import MiddlewareBase, MiddlewareChain
from app.core.parallel import ParallelToolExecutor
from app.core.persistent_memory import PersistentMemoryService
from app.core.task_state_machine import TaskState, TaskStateMachine
from app.core.tool_prioritizer import ToolPrioritizer
from app.core.tracing import Span, SpanKind, SpanStatus, TracingContext, get_current_trace, trace_store
from app.models.openai_adapter import OpenAIAdapter
from app.models.registry import ModelRegistry
from app.tools import ToolRegistry


class AgentSession:
    def __init__(self, session_id: str, agent_id: str, user_id: str, provider: str, model_id: str, api_key: str, base_url: str | None = None, system_prompt: str = "", tools: list[str] | None = None, context_config: ContextConfig | None = None, mode: str = "act"):
        self.session_id = session_id
        self.agent_id = agent_id
        self.user_id = user_id
        self.provider = provider
        self.model_id = model_id
        self.api_key = api_key
        self.base_url = base_url
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.context_config = context_config or ContextConfig()
        self.max_iterations = 10
        self.messages: list[dict[str, Any]] = []
        self._stop_requested = False
        self.session_memory = _SessionMemory(self)
        self.current_turn_id: str | None = None
        self.event_replay = EventReplayBuffer()
        # State machine: use TaskState for unified lifecycle management
        self.state_machine = TaskStateMachine(task_id=session_id, initial_state=TaskState.PENDING)
        attach_session_recorder(self)
        # Agent mode: plan (read-only) or act (real execution)
        self.mode = mode
        # Debug tracking per task
        self.debug_attempts: dict[str, int] = {}
        # Survival layer: restart tracking
        self.restart_count: int = 0
        self.paused_at: str | None = None
        self.termination_reason: str | None = None
        # Permission system
        try:
            from app.core.permission_rules import get_default_config
            self.permission_config = get_default_config()
        except Exception:
            self.permission_config = None
        # Fire-and-forget task tracking
        self._pending_tasks: set[asyncio.Task] = set()

    @property
    def status(self) -> SessionStatus:
        """Map TaskState to legacy SessionStatus for backward compatibility."""
        mapping = {
            TaskState.PENDING: SessionStatus.PENDING,
            TaskState.PROCESSING: SessionStatus.RUNNING,
            TaskState.PAUSED: SessionStatus.PAUSED,
            TaskState.COMPLETED: SessionStatus.COMPLETED,
            TaskState.FAILED: SessionStatus.FAILED,
            TaskState.CANCELLED: SessionStatus.STOPPED,
        }
        return mapping.get(self.state_machine.state, SessionStatus.PENDING)

    def stop(self) -> None:
        self._stop_requested = True
        try:
            asyncio.get_running_loop()
            _spawn(self.state_machine.transition(TaskState.CANCELLED, trigger="user_stop"))
        except RuntimeError:
            pass

    async def pause(self) -> None:
        """Pause the session, recording the pause timestamp."""
        await self.state_machine.transition(TaskState.PAUSED, trigger="user_pause")
        self.paused_at = datetime.now(UTC).replace(tzinfo=None).isoformat()

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
        """Create a background task and track it for cleanup."""
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)
        return task

    async def _await_pending_tasks(self) -> None:
        """Await all pending fire-and-forget tasks and clear the set."""
        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)
            self._pending_tasks.clear()


class _SessionMemory:
    def __init__(self, session: AgentSession):
        self._session = session

    def add(self, role: str, content: str) -> None:
        self._session.messages.append({"role": role, "content": content})


class AgentEngine:
    def __init__(self, model_registry: ModelRegistry | None = None, tool_registry: ToolRegistry | None = None, checkpoint_store: InMemoryCheckpointStore | None = None, middlewares: list[MiddlewareBase] | None = None):
        self.model_registry = model_registry or di_resolve("ModelRegistry")
        self.tool_registry = tool_registry or di_resolve("ToolRegistry")
        self._checkpoints = checkpoint_store or InMemoryCheckpointStore()
        self._sessions: dict[str, AgentSession] = {}
        self._session_locks: dict[str, asyncio.Lock] = {}
        self.memory_service = PersistentMemoryService()
        # Build default middleware stack
        default_middlewares = self._build_default_middlewares()
        # Merge with user-provided middlewares (user middlewares take precedence)
        all_middlewares = default_middlewares + (middlewares or [])
        # Middleware chain for composable hooks
        self._middleware_chain = MiddlewareChain(all_middlewares)
        # Event bus for decoupled event handling
        from app.core.event_bus import get_event_bus
        self._event_bus = get_event_bus()
        # Tool prioritization with lightweight learning (reference: Suna)
        self.tool_prioritizer = ToolPrioritizer()
        # Batch message buffer: accumulates pending writes per session for flush
        self._msg_buffers: dict[str, list[dict]] = {}
        self._msg_flush_interval = 2.0  # seconds between forced flushes
        self._msg_last_flush: dict[str, float] = {}
        # Background task for periodic flush
        self._flush_task: asyncio.Task | None = None
        # Auto-debug loop (reference: Devika failure debugging closed loop)
        try:
            from app.core.debug_loop import DebugLoopEngine
            self.debug_loop = DebugLoopEngine(model_registry=self.model_registry)
        except Exception:
            self.debug_loop = None
        # Security sandbox: rejects hazard commands and out-of-scope file access before execution
        try:
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
        except Exception:
            self.sandbox = None
            self.permission_overlay = None
            self.agent_mode = None
        # Default permission config for new sessions
        try:
            from app.core.permission_rules import get_default_config
            self._default_permission_config = get_default_config()
        except Exception:
            self._default_permission_config = None

    def _setup_default_permissions(self) -> None:
        """Setup default three-layer permission rules."""
        from app.core.security_sandbox import PermissionLevel, PermissionRule
        defaults = [
            PermissionRule(action="read", resource_pattern="*", level=PermissionLevel.ALLOW, description="Read any file"),
            PermissionRule(action="write", resource_pattern="./data/*", level=PermissionLevel.ALLOW, description="Write to data dir"),
            PermissionRule(action="write", resource_pattern="*", level=PermissionLevel.ALLOW, description="Write any file"),
            PermissionRule(action="execute", resource_pattern="*", level=PermissionLevel.ALLOW, description="Execute any command"),
            PermissionRule(action="delete", resource_pattern="*", level=PermissionLevel.DENY, description="Delete forbidden"),
        ]
        self.permission_overlay.set_defaults(defaults)

    def _build_default_middlewares(self) -> list[MiddlewareBase]:
        """Build the default middleware stack."""
        middlewares = []
        try:
            from app.core.middleware_self_healing import SelfHealingMiddleware
            middlewares.append(SelfHealingMiddleware(max_retries=2))
        except Exception as exc:
            logger.warning("agent_engine.default_self_healing_unavailable", error=str(exc))
        try:
            from app.core.middleware_permission import PermissionMiddleware
            middlewares.append(PermissionMiddleware(max_calls_per_minute=120))
        except Exception as exc:
            logger.warning("agent_engine.default_permission_unavailable", error=str(exc))
        return middlewares

    def _get_degraded_sandbox(self):
        """Build a fallback read-only SecuritySandbox from environment when init failed."""
        try:
            from app.core.security_sandbox import SandboxConfig, SecuritySandbox
            workdir = os.environ.get("CLIMBER_SANDBOX_WORKDIR") or os.getcwd()
            return SecuritySandbox(SandboxConfig(workdir=workdir))
        except Exception:
            return None

    # Tool names that accept a shell command under a "command" parameter
    _COMMAND_TOOLS = {
        "run_command",
        "shell",
        "execute_command",
        "bash",
        "native_run",
        "stream_command",
        "container_exec",
    }
    # Media tools that execute shell-like commands under a "command" parameter
    _MEDIA_TOOLS = {
        "process_video",
        "process_image",
    }
    # Tool names that perform file IO under path/file parameters
    _FILE_TOOLS = {
        "read_file": ("path", "read"),
        "write_file": ("path", "write"),
        "edit_file": ("path", "write"),
        "append_file": ("path", "write"),
        "native_read_file": ("path", "read"),
        "native_write_file": ("path", "write"),
        "native_list_dir": ("path", "read"),
        "download_file": ("output_path", "write"),
        "file_exists": ("path", "read"),
        "file_info": ("path", "read"),
        "file_diff": ("path", "read"),
        "list_directory": ("dir", "read"),
        "list_files": ("directory", "read"),
    }

    def _validate_tool_call(self, session: AgentSession, tool_name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        """Pre-execution safety check. Returns (allowed, reason)."""
        approval_reason: str | None = None
        # PLAN mode: deny write/execute operations, but allow edit_file (preview-only)
        if hasattr(self, 'agent_mode') and self.agent_mode is not None:
            from app.core.security_sandbox import AgentMode
            if self.agent_mode == AgentMode.PLAN and tool_name in self._COMMAND_TOOLS:
                return False, "PLAN mode: command execution is read-only"
            if self.agent_mode == AgentMode.PLAN and tool_name in self._FILE_TOOLS:
                param, mode = self._FILE_TOOLS[tool_name]
                if mode != "read" and tool_name != "edit_file":
                    return False, "PLAN mode: file modification is read-only"

        # New permission rules system check
        if session.permission_config is not None:
            from app.core.permission_rules import RuleDecision
            decision = session.permission_config.evaluate(tool_name, arguments)
            if decision == RuleDecision.DENY:
                return False, f"Permission denied by rules: {tool_name}"
            if decision == RuleDecision.ASK:
                approval_reason = f"Approval required: {tool_name}"

        # Permission overlay check (legacy)
        if self.permission_overlay is not None:
            action = "execute" if tool_name in self._COMMAND_TOOLS else "read"
            if tool_name in self._FILE_TOOLS:
                _, mode = self._FILE_TOOLS[tool_name]
                action = mode
            resource = arguments.get("path") or arguments.get("command") or "*"
            level = self.permission_overlay.evaluate(action, str(resource), agent_id=None, user_id=None)
            from app.core.security_sandbox import PermissionLevel
            if level == PermissionLevel.DENY:
                return False, f"Permission denied by overlay: {action} on {resource}"
            if level == PermissionLevel.ASK:
                approval_reason = f"Approval required: {action} on {resource}"

        # JSON Schema validation
        tool_def = self.tool_registry.get_tool(tool_name)
        try:
            from app.core.security_sandbox import validate_tool_input
            if tool_def and tool_def.parameters:
                validate_tool_input(tool_def.parameters, arguments)
        except Exception as e:
            return False, str(e)

        # Existing sandbox checks
        if self.sandbox is None:
            explicitly_safe = bool(tool_def and tool_def.sandbox_safe_when_unavailable)
            if not explicitly_safe:
                return False, f"Security sandbox unavailable: refusing unclassified or side-effecting tool {tool_name}"
            if tool_name in self._COMMAND_TOOLS or tool_name in self._MEDIA_TOOLS:
                return False, f"Security sandbox unavailable: refusing command execution {tool_name}"
            if tool_name in self._FILE_TOOLS:
                _, mode = self._FILE_TOOLS[tool_name]
                if mode != "read":
                    return False, f"Security sandbox unavailable: refusing write tool {tool_name}"
                path = arguments.get("path") or arguments.get("directory") or arguments.get("dir") or ""
                if path:
                    degraded = self._get_degraded_sandbox()
                    if degraded is not None:
                        ok, reason = degraded.validate_file_access(path, "read")
                        if not ok:
                            return False, f"blocked by degraded sandbox: {reason}"
                    else:
                        return False, "Security sandbox unavailable and cannot build fallback"
            return True, approval_reason or "OK"
        try:
            if tool_name in self._COMMAND_TOOLS or tool_name in self._MEDIA_TOOLS:
                cmd = arguments.get("command") or ""
                if isinstance(cmd, str) and cmd:
                    ok, reason = self.sandbox.validate_command(cmd)
                    if not ok:
                        return False, reason
            if tool_name in self._FILE_TOOLS:
                param, mode = self._FILE_TOOLS[tool_name]
                path = arguments.get(param) or arguments.get("path") or ""
                if isinstance(path, str) and path:
                    ok, reason = self.sandbox.validate_file_access(path, mode)
                    if not ok:
                        return False, reason
        except Exception as e:
            return False, f"sandbox validation error: {e}"
        return True, approval_reason or "OK"

    def create_session(self, agent_id: str, user_id: str, provider: str, model_id: str, api_key: str, base_url: str | None = None, system_prompt: str = "", tools: list[str] | None = None, context_config: ContextConfig | None = None, session_id: str | None = None) -> AgentSession:
        from uuid import uuid4
        session_id = session_id or str(uuid4())
        session = AgentSession(
            session_id=session_id,
            agent_id=agent_id,
            user_id=user_id,
            provider=provider,
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
            system_prompt=system_prompt,
            tools=tools,
            context_config=context_config,
        )
        # Apply engine's default permission config
        if hasattr(self, '_default_permission_config') and self._default_permission_config is not None:
            session.permission_config = self._default_permission_config
        if system_prompt:
            session.messages.append({"role": MessageRole.SYSTEM, "content": system_prompt})
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> AgentSession | None:
        """Return the in-memory session for an id, or ``None`` when absent."""
        return self._sessions.get(session_id)

    def register_session(self, session: AgentSession) -> AgentSession:
        """Register an already-created session under its id and return it."""
        self._sessions[session.session_id] = session
        return session

    def get_session_lock(self, session_id: str) -> asyncio.Lock | None:
        """Return the per-session concurrency lock if one exists."""
        return self._session_locks.get(session_id)

    def drop_session_lock(self, session_id: str) -> None:
        """Drop the per-session lock entry (safe on repeated calls)."""
        self._session_locks.pop(session_id, None)

    def has_active_session(self, session_id: str) -> bool:
        """True when an in-memory session exists for the id."""
        return session_id in self._sessions

    async def _persist_message(
        self,
        session_id: str,
        role: str,
        content: str | None = None,
        tool_calls: list[dict] | None = None,
        tool_name: str | None = None,
        tokens: int = 0,
        run_id: str | None = None,
    ) -> None:
        """Persist a message via batch buffer (flushes every ~2s or on buffer full)."""
        try:
            await record(
                session_id,
                "message",
                {
                    "role": role,
                    "content": content,
                    "tool_calls": tool_calls or [],
                    "tool_name": tool_name,
                    "tokens": tokens,
                    "run_id": run_id,
                },
            )
            now = time.monotonic()
            buf = self._msg_buffers.setdefault(session_id, [])
            if not buf:
                self._msg_last_flush[session_id] = now
            buf.append({
                "session_id": session_id,
                "run_id": run_id,
                "role": role,
                "content": content,
                "tool_calls": tool_calls or [],
                "tool_name": tool_name,
                "tokens": tokens,
            })

            if len(buf) >= 10 or (now - self._msg_last_flush.get(session_id, now) >= self._msg_flush_interval):
                await self._flush_buffer(session_id)
        except Exception:
            logger.debug("agent_engine.suppressed", exc_info=True)

    async def _flush_buffer(self, session_id: str) -> None:
        """Batch-commit all pending messages for one session."""
        buf = self._msg_buffers.get(session_id, [])
        if not buf:
            return
        try:
            from app.storage import async_session
            from app.storage.database import Message
            async with async_session() as db:
                for item in buf:
                    db.add(Message(**item))
                await db.commit()
            self._msg_buffers.pop(session_id, None)
            self._msg_last_flush[session_id] = time.monotonic()
        except Exception:
            logger.warning("agent_engine.msg_flush_failed", session_id=session_id, buffered=len(buf))

    async def _record_raw_payload(self, session: AgentSession, *, run_id: str, result: ChatResult) -> None:
        """Persist the provider payload snapshot for a Run.

        Observability recording must never break the business Run, so every
        failure degrades to a warning.
        """
        try:
            from app.core.raw_payload import build_raw_payload, load_raw_payload_config
            from app.storage import async_session as run_store_session_factory
            from app.storage.run_store import SQLAlchemyRunStore

            config = load_raw_payload_config()
            raw = getattr(result, "raw", None) or {
                "choices": [
                    {
                        "finish_reason": result.finish_reason,
                        "message": {"content": result.content, "tool_calls": result.tool_calls},
                    }
                ],
                "usage": {"total_tokens": result.tokens_used},
            }
            snapshot = build_raw_payload(
                run_id=run_id,
                message_id=None,
                provider=session.provider,
                model=session.model_id,
                raw=raw,
                config=config,
            )
            await SQLAlchemyRunStore(session_factory=run_store_session_factory).save_raw_payload(snapshot)
        except Exception:
            logger.warning("agent_engine.raw_payload_persist_failed", run_id=run_id, exc_info=True)


    def _model_retry_settings(self) -> tuple[int, float]:
        import os
        max_retries = int(os.environ.get("MODEL_MAX_RETRIES", "2"))
        delay = float(os.environ.get("MODEL_RETRY_DELAY", "2.0"))
        return max_retries, delay

    async def _stream_with_retry(
        self,
        adapter: Any,
        messages: list[dict],
        tools: list[dict] | None,
    ) -> tuple[list[tuple[str, list[dict]]], int]:
        max_retries, delay = self._model_retry_settings()
        attempt = 0
        while True:
            events: list[tuple[str, list[dict]]] = []
            total_tokens = 0
            chunks = 0
            try:
                async for chunk in adapter.stream_chat(messages=messages, tools=tools):
                    chunks += 1
                    content = chunk.content or ""
                    tool_calls = list(chunk.tool_calls) if chunk.tool_calls else []
                    events.append((content, tool_calls))
                    if hasattr(chunk, 'usage') and chunk.usage:
                        total_tokens = chunk.usage
                    elif hasattr(chunk, 'tokens_used') and chunk.tokens_used:
                        total_tokens = chunk.tokens_used
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if attempt >= max_retries or chunks > 0:
                    logger.warning("llm_stream_failed", attempt=attempt, chunks=chunks, error=str(exc))
                    raise
                attempt += 1
                logger.warning("llm_stream_retrying", attempt=attempt, chunks=chunks, error=str(exc))
                await asyncio.sleep(delay * attempt)
                continue
            if chunks == 0 and attempt < max_retries:
                attempt += 1
                logger.warning("llm_stream_empty_retrying", attempt=attempt)
                await asyncio.sleep(delay * attempt)
                continue
            return events, total_tokens

    async def _chat_with_retry(
        self,
        adapter: Any,
        messages: list[dict],
        tools: list[dict] | None,
    ) -> ChatResult:
        max_retries, delay = self._model_retry_settings()
        attempt = 0
        while True:
            try:
                return await adapter.chat(messages=messages, tools=tools)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if attempt >= max_retries:
                    logger.warning("llm_chat_failed", attempt=attempt, error=str(exc))
                    raise
                attempt += 1
                logger.warning("llm_chat_retrying", attempt=attempt, error=str(exc))
                await asyncio.sleep(delay * attempt)

    async def run(
        self,
        session: AgentSession,
        message: str,
        *,
        run_id: str | None = None,
        trace_id: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        # Acquire session-level lock to prevent concurrent requests.
        # Lock is tied to session lifetime (created on first use, never popped),
        # ensuring mutual exclusion across all requests to the same session.
        if session.session_id not in self._session_locks:
            self._session_locks[session.session_id] = asyncio.Lock()

        lock = self._session_locks[session.session_id]
        if lock.locked():
            yield AgentEvent(type=AgentEventType.ERROR, data={"error": "Session is busy processing another request"})
            return

        async with lock:
            async with TracingContext(
                name=f"agent:{session.agent_id or 'agent'}",
                kind=SpanKind.AGENT_SESSION,
                user_id=session.user_id,
                trace_id=trace_id,
                metadata={
                    "session_id": session.session_id,
                    "agent_id": session.agent_id,
                    "model": session.model_id,
                    "run_id": run_id,
                },
            ) as trace_ctx:
                trace_ctx.span.set_input(message)
                async for event in self._run_locked(session, message, run_id=run_id):
                    session.event_replay.append(
                        event.type.value,
                        event.data,
                        turn_id=session.current_turn_id or "",
                    )
                    if event.type.value in RECORDED_AGENT_EVENTS:
                        await record(
                            session.session_id,
                            event.type.value,
                            {"turn_id": session.current_turn_id or "", **event.data},
                        )
                    yield event

    @staticmethod
    def replay_events(
        session: AgentSession,
        after_sequence: int = 0,
        turn_id: str | None = None,
    ) -> list[ReplayRecord]:
        """Return retained session events after a reconnect cursor."""
        return session.event_replay.after(after_sequence, turn_id=turn_id)

    @staticmethod
    def _checkpoint_id(session: AgentSession, iteration: int) -> str:
        """Return a stable, cross-turn-unique checkpoint identifier."""
        turn_marker = session.current_turn_id or session.session_id
        identity = f"climber-checkpoint:{session.session_id}:{turn_marker}:{iteration}"
        return str(uuid5(NAMESPACE_URL, identity))

    async def run_agent(self, session: AgentSession, message: str) -> dict[str, Any]:
        """Convenience wrapper around run() that collects output into a dict.

        Returns {"output": str} on success, or {"error": str} on failure.
        """
        output: list[str] = []
        error: str | None = None
        try:
            async for event in self.run(session, message):
                if event.type is AgentEventType.DONE:
                    content = event.data.get("content")
                    if content:
                        output.append(content)
                elif event.type is AgentEventType.ERROR:
                    error = event.data.get("error") or "Unknown error"
        except Exception as e:
            error = str(e)
        if error:
            return {"error": error}
        return {"output": "".join(output)}


    async def _run_locked(
        self,
        session: AgentSession,
        message: str,
        *,
        run_id: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Internal run method — executes under session lock."""
        session.current_turn_id = run_id or str(uuid4())
        # Allow restart: COMPLETED/FAILED/CANCELLED sessions must reset to PENDING first
        current = session.state_machine.state
        if current in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
            await session.state_machine.transition(TaskState.PENDING, trigger="user_restart")
        # Transition to PROCESSING state via state machine
        await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")
        session.messages.append({"role": MessageRole.USER, "content": message})
        await self._persist_message(session.session_id, MessageRole.USER, content=message, run_id=run_id)

        # Set current agent mode for tool execution context (e.g., PLAN vs ACT)
        try:
            from app.core.file_patch import set_current_agent_mode
            set_current_agent_mode(session.mode)
        except Exception:
            logger.debug("agent_engine.suppressed", exc_info=True)

        # Fire-and-forget notification for agent start
        try:
            from app.services.notifications import notification_service
            _spawn(notification_service.agent_message(session.agent_id or "Agent", "开始执行任务..."))
        except Exception:
            logger.debug("agent_engine.suppressed", exc_info=True)

        # Retrieve relevant memories and inject into context (replace if already present)
        try:
            memory_context = await self.memory_service.format_memories_for_prompt(
                user_id=session.user_id,
                query=message,
                max_memories=5,
            )
            if memory_context:
                memory_marker = "<!-- MEMORY_CONTEXT -->"
                for i, msg in enumerate(session.messages):
                    if msg.get("content", "").startswith(memory_marker):
                        session.messages[i] = {"role": MessageRole.SYSTEM, "content": memory_marker + "\n" + memory_context}
                        break
                else:
                    session.messages.insert(-1, {"role": MessageRole.SYSTEM, "content": memory_marker + "\n" + memory_context})
        except Exception:
            logger.debug("agent_engine.suppressed", exc_info=True)

        # Inject Core Memory blocks as XML into system prompt (replace if already present)
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
        except Exception:
            logger.debug("agent_engine.suppressed", exc_info=True)

        iteration = 0
        executor = ParallelToolExecutor(
            self.tool_registry,
            validator=lambda name, args: self._validate_tool_call(session, name, args),
            session=session,
        )

        async def retry_tool(tool_name: str, arguments: dict[str, Any]) -> str:
            allowed, reason = self._validate_tool_call(session, tool_name, arguments)
            if not allowed:
                return f"blocked by sandbox: {reason}"
            if reason.startswith("Approval required"):
                return f"permission denied: {reason}"
            return await self.tool_registry.execute(tool_name, arguments)
        compressor = ContextCompressor(session.context_config)
        result: ChatResult | None = None
        trace_ctx = get_current_trace()

        try:
            adapter = self.model_registry.get_or_create(
                provider=session.provider,
                model_id=session.model_id,
                api_key=session.api_key,
                base_url=session.base_url,
            )

            tools = self._build_tools(session.tools, task_description=message)

            while iteration < session.max_iterations and not session._stop_requested:
                iteration += 1
                yield AgentEvent(type=AgentEventType.THINKING, data={"iteration": iteration})
                # Emit iteration start event
                await self._event_bus.publish("iteration_start", {
                    "session_id": session.session_id,
                    "iteration": iteration,
                    "message_count": len(session.messages),
                })

                ctx_tokens = estimate_tokens(session.messages)
                ctx_limit = getattr(adapter.capabilities, "max_tokens", None) or session.context_config.max_tokens
                if compressor.needs_compression(session.messages) or (ctx_limit and ctx_tokens > ctx_limit * 0.8):
                    session.messages = await compressor.compress(session.messages, adapter)
                    yield AgentEvent(type=AgentEventType.CONTEXT_COMPRESSION, data={"iteration": iteration, "tokens": ctx_tokens, "limit": ctx_limit})

                llm_cm = (
                    trace_ctx.child_span(f"llm_call:{iteration}", SpanKind.LLM_CALL)
                    if trace_ctx is not None
                    else nullcontext()
                )

                # Wrap LLM call with reasoning middleware if any
                if self._middleware_chain.has_reasoning_middleware:
                    llm_input = {"adapter": adapter, "messages": session.messages, "tools": tools, "iteration": iteration}

                    async def _llm_with_middleware(llm_cm=llm_cm):
                        async with llm_cm as llm_span:
                            try:
                                if adapter.capabilities.streaming:
                                    events, total_tokens = await self._stream_with_retry(adapter, session.messages, tools or None)
                                    full_content = ""
                                    accumulated_tool_calls = []
                                    for delta_content, tool_calls in events:
                                        if session._stop_requested:
                                            yield AgentEvent(type=AgentEventType.STOPPED, data={"reason": "user_requested"})
                                            await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
                                            return
                                        if delta_content:
                                            full_content += delta_content
                                            yield AgentEvent(type=AgentEventType.TEXT, data={"content": delta_content})
                                        if tool_calls:
                                            accumulated_tool_calls = tool_calls
                                    yield ("result", ChatResult(content=full_content, tool_calls=accumulated_tool_calls, finish_reason="stop", tokens_used=total_tokens))
                                else:
                                    r = await self._chat_with_retry(adapter, session.messages, tools or None)
                                    if llm_span is not None:
                                        llm_span.set_tokens(getattr(r, "tokens_used", 0) or 0, model=session.model_id)
                                        llm_span.set_output(r.content if r else "")
                                    yield ("result", r)
                            except Exception as e:
                                if llm_span is not None:
                                    llm_span.set_error(str(e))
                                if session._stop_requested:
                                    yield ("error", str(e))
                                    return
                                yield ("error", str(e))

                    async for event in self._middleware_chain.execute_reasoning(self, session, llm_input, _llm_with_middleware):
                        if isinstance(event, tuple) and event[0] == "result":
                            result = event[1]
                        elif isinstance(event, tuple) and event[0] == "error":
                            yield AgentEvent(type=AgentEventType.ERROR, data={"error": event[1]})
                            await session.state_machine.transition(TaskState.FAILED, trigger="llm_error")
                            if trace_ctx is not None:
                                trace_ctx.span.set_error(event[1])
                            return
                        elif isinstance(event, AgentEvent):
                            yield event
                else:
                    async with llm_cm as llm_span:
                        try:
                            if adapter.capabilities.streaming:
                                events, total_tokens = await self._stream_with_retry(adapter, session.messages, tools or None)
                                full_content = ""
                                accumulated_tool_calls = []
                                for delta_content, tool_calls in events:
                                    if session._stop_requested:
                                        yield AgentEvent(type=AgentEventType.STOPPED, data={"reason": "user_requested"})
                                        await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
                                        return
                                    if delta_content:
                                        full_content += delta_content
                                        yield AgentEvent(type=AgentEventType.TEXT, data={"content": delta_content})
                                    if tool_calls:
                                        accumulated_tool_calls = tool_calls
                                result = ChatResult(content=full_content, tool_calls=accumulated_tool_calls, finish_reason="stop", tokens_used=total_tokens)
                            else:
                                result = await self._chat_with_retry(adapter, session.messages, tools or None)
                            if llm_span is not None:
                                llm_span.set_tokens(getattr(result, "tokens_used", 0) or 0, model=session.model_id)
                                llm_span.set_output(result.content if result else "")
                        except Exception as e:
                            if llm_span is not None:
                                llm_span.set_error(str(e))
                            if session._stop_requested:
                                yield AgentEvent(type=AgentEventType.ERROR, data={"error": str(e)})
                                await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
                                return
                            yield AgentEvent(type=AgentEventType.ERROR, data={"error": str(e)})
                            await session.state_machine.transition(TaskState.FAILED, trigger="llm_error")
                            if trace_ctx is not None:
                                trace_ctx.span.set_error(str(e))
                            return

                # Persist the provider payload snapshot under the raw payload policy.
                if run_id is not None:
                    await self._record_raw_payload(session, run_id=run_id, result=result)

                # Parse XML-style tool calls for non-standard providers (e.g., StepFun)
                if not result.tool_calls and result.content:
                    xml_tool_calls = OpenAIAdapter._parse_xml_tool_calls(result.content)
                    if xml_tool_calls:
                        result.tool_calls = xml_tool_calls
                        cleaned = re.sub(r'<function=[^>]+/?>|</function>', '', result.content, flags=re.DOTALL | re.IGNORECASE).strip()
                        if not cleaned:
                            result.content = ""

                if result.content:
                    session.messages.append({"role": MessageRole.ASSISTANT, "content": result.content})
                    await self._persist_message(
                        session.session_id,
                        MessageRole.ASSISTANT,
                        content=result.content,
                        tokens=getattr(result, 'tokens_used', 0),
                        run_id=run_id,
                    )
                    # Emit TEXT event for non-streaming path (streaming path emits per-chunk)
                    if not (adapter.capabilities and adapter.capabilities.streaming):
                        yield AgentEvent(type=AgentEventType.TEXT, data={"content": result.content})

                if not result.tool_calls and not result.content:
                    session.messages.append({
                        "role": MessageRole.SYSTEM,
                        "content": "Your previous response was empty. Please provide a helpful response or use an appropriate tool.",
                    })
                    continue

                if result.tool_calls:
                    session.messages.append({"role": MessageRole.ASSISTANT, "content": "", "tool_calls": result.tool_calls})
                    await self._persist_message(
                        session.session_id,
                        MessageRole.ASSISTANT,
                        content="",
                        tool_calls=result.tool_calls,
                        run_id=run_id,
                    )
                    for tc in result.tool_calls:
                        yield AgentEvent(type=AgentEventType.TOOL_CALL, data={"id": tc.get("id"), "name": tc.get("function", {}).get("name"), "arguments": tc.get("function", {}).get("arguments", {})})
                    # Emit tool batch start event
                    await self._event_bus.publish("tool_batch_start", {
                        "session_id": session.session_id,
                        "tool_count": len(result.tool_calls),
                        "tool_names": [tc.get("function", {}).get("name") for tc in result.tool_calls],
                    })
                    tool_results = await executor.execute_all(result.tool_calls)
                    for tr in tool_results:
                        policy_rejection = tr.error.startswith(("blocked by sandbox:", "permission denied:"))
                        if self.debug_loop and tr.error and not policy_rejection:
                            key = tr.tool_name
                            attempts = session.debug_attempts.get(key, 0)
                            if attempts < 3:
                                session.debug_attempts[key] = attempts + 1
                                fixed = await self.debug_loop.recover(
                                    tool_name=tr.tool_name,
                                    arguments=tr.arguments or {},
                                    error_output=tr.error or tr.result,
                                    retry_callback=retry_tool,
                                )
                                recovery_blocked = bool(
                                    fixed
                                    and fixed.output
                                    and fixed.output.startswith(("blocked by sandbox:", "permission denied:"))
                                )
                                if fixed and fixed.success and fixed.output and not recovery_blocked:
                                    tr.error = ""
                                    tr.result = fixed.output
                                    tr.success = True

                        self.tool_prioritizer.record_outcome(
                            tr.tool_name,
                            tr.success,
                            tr.duration_ms,
                        )
                        yield AgentEvent(
                            type=AgentEventType.TOOL_RESULT,
                            data={
                                "id": tr.tool_call_id,
                                "tool_call_id": tr.tool_call_id,
                                "tool_name": tr.tool_name,
                                "result": tr.result,
                                "error": tr.error,
                            },
                        )

                        tool_content = tr.error or tr.result
                        session.messages.append({"role": MessageRole.TOOL, "content": tool_content, "tool_call_id": tr.tool_call_id or tr.tool_name})
                        await self._persist_message(
                            session.session_id,
                            MessageRole.TOOL,
                            content=tool_content,
                            tool_name=tr.tool_name,
                            run_id=run_id,
                        )

                        if trace_ctx is not None:
                            tool_span = Span(
                                name=f"tool:{tr.tool_name}",
                                kind=SpanKind.TOOL_CALL,
                                trace_id=trace_ctx.span.trace_id,
                                parent_id=trace_ctx.span.id,
                                user_id=session.user_id,
                                metadata={"session_id": session.session_id},
                            )
                            tool_span.tool_name = tr.tool_name
                            tool_span.set_input(tr.arguments or {})
                            tool_span.set_output(tr.result)
                            tool_span.duration_ms = tr.duration_ms or 0
                            if tr.error:
                                tool_span.set_error(tr.error)
                            await trace_store.save_span(tool_span)

                    # Enhanced checkpoint with LangGraph-style channel values
                    cp = CheckpointData(
                        session_id=session.session_id,
                        messages=session.messages,
                        iteration=iteration,
                        status=session.state_machine.state.value,
                        channel_values={
                            "last_tool_calls": result.tool_calls,
                            "last_tool_results": [tr.result for tr in tool_results],
                            "context_tokens": ctx_tokens,
                        },
                        channel_versions={"messages": iteration, "tools": len(result.tool_calls)},
                        versions_seen={"node": {"messages": iteration, "tools": len(result.tool_calls)}},
                    )
                    await self._checkpoints.save(
                        None,
                        cp,
                        thread_id=session.current_turn_id,
                        checkpoint_id=self._checkpoint_id(session, iteration),
                    )
                    yield AgentEvent(type=AgentEventType.CHECKPOINT, data={"iteration": iteration, "tool_calls": len(result.tool_calls)})

                    continue

                # Enhanced final checkpoint
                cp = CheckpointData(
                    session_id=session.session_id,
                    messages=session.messages,
                    iteration=iteration,
                    status=session.state_machine.state.value,
                    channel_values={
                        "final_content": result.content,
                        "total_iterations": iteration,
                        "context_tokens": ctx_tokens,
                    },
                    channel_versions={"messages": iteration},
                    versions_seen={"node": {"messages": iteration}},
                )
                await self._checkpoints.save(
                    None,
                    cp,
                    thread_id=session.current_turn_id,
                    checkpoint_id=self._checkpoint_id(session, iteration),
                )
                yield AgentEvent(type=AgentEventType.CHECKPOINT, data={"iteration": iteration})
                break

            if iteration >= session.max_iterations and result and result.tool_calls:
                await session.state_machine.transition(TaskState.FAILED, trigger="max_iterations")
                if trace_ctx is not None:
                    trace_ctx.span.set_status(SpanStatus.ERROR)
                yield AgentEvent(type=AgentEventType.DONE, data={"status": "max_iterations_reached", "iterations": iteration})
                return

            if session._stop_requested:
                await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
            else:
                await session.state_machine.transition(TaskState.COMPLETED, trigger="run_complete")
                # Emit session complete event
                await self._event_bus.publish("session_complete", {
                    "session_id": session.session_id,
                    "iterations": iteration,
                    "status": "completed",
                })
                try:
                    from app.services.notifications import notification_service
                    _spawn(notification_service.task_complete(f"Agent {session.agent_id}", result.content[:100] if result and result.content else None))
                except Exception:
                    logger.debug("agent_engine.suppressed", exc_info=True)

        except Exception as e:
            if session._stop_requested:
                await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
            else:
                await session.state_machine.transition(TaskState.FAILED, trigger="unhandled_error")
            # Emit session error event
            await self._event_bus.publish("session_error", {
                "session_id": session.session_id,
                "error": str(e),
            })
            yield AgentEvent(type=AgentEventType.ERROR, data={"error": str(e)})
            if trace_ctx is not None:
                trace_ctx.span.set_error(str(e))
            try:
                from app.services.notifications import notification_service
                _spawn(notification_service.task_failed(f"Agent {session.agent_id}", str(e)))
            except Exception:
                logger.debug("agent_engine.suppressed", exc_info=True)
            return

        # Store important interaction in episodic memory
        try:
            if result and result.content and len(result.content) > 10:
                await self.memory_service.create_episodic_memory(
                    user_id=session.user_id,
                    content=f"User: {message}\nAssistant: {result.content[:500]}",
                    agent_id=session.agent_id,
                    source_session_id=session.session_id,
                    importance=0.7,
                )
        except Exception:
            logger.debug("agent_engine.suppressed", exc_info=True)

        # Trigger memory reflection (fire-and-forget)
        try:
            from app.core.memory_reflection import memory_reflection
            _spawn(memory_reflection.maybe_reflect(session.user_id))
        except Exception:
            logger.debug("agent_engine.suppressed", exc_info=True)

        yield AgentEvent(type=AgentEventType.DONE, data={"status": session.status.value, "iterations": iteration, "content": result.content if result else "", "tokens_used": getattr(result, 'tokens_used', 0) if result else 0})



    def _build_tools(self, tool_names: list[str], task_description: str = "") -> list[dict[str, Any]]:
        if task_description and len(tool_names) > 1:
            name_to_defn = {name: self.tool_registry.get_tool(name) for name in tool_names}
            available = [
                {"type": "function", "function": {"name": d.name, "description": d.description, "parameters": d.parameters}}
                for name, d in name_to_defn.items() if d
            ]
            ranked = self.tool_prioritizer.rank_tools(task_description, available)
            tool_names = [name for name in ranked if name in name_to_defn]
        result = []
        for name in tool_names:
            defn = self.tool_registry.get_tool(name)
            if defn:
                result.append({
                    "type": "function",
                    "function": {
                        "name": defn.name,
                        "description": defn.description,
                        "parameters": defn.parameters,
                    },
                })
        return result

    # === Permission Management ===

    def resolve_permission(self, tool_call_id: str, decision: str) -> bool:
        """Resolve a pending permission request via the approval_manager.

        This bridges the legacy resolve_permission API to the active approval
        system so the frontend can approve/reject tool calls in-flight.
        """
        from app.core.approval import approval_manager

        request = approval_manager.resolve(tool_call_id, decision, resolved_by="human")
        return request is not None

    async def resolve_permission_async(
        self,
        tool_call_id: str,
        decision: str,
        user_id: str | None = None,
    ) -> bool:
        """Resolve a permission request through the durable atomic API."""
        from app.core.approval import approval_manager

        request = await approval_manager.resolve_async(
            tool_call_id,
            decision,
            resolved_by="human",
            user_id=user_id,
        )
        return request is not None

    def get_permission_config(self) -> Any:
        """Get the current default permission configuration."""
        return self._default_permission_config

    def update_permission_config(self, config: Any) -> None:
        """Update the default permission configuration for new sessions."""
        self._default_permission_config = config

    async def _periodic_flush(self) -> None:
        """Background task: flush all message buffers every 2 seconds."""
        while True:
            await asyncio.sleep(self._msg_flush_interval)
            for session_id in list(self._msg_buffers.keys()):
                if time.monotonic() - self._msg_last_flush.get(session_id, 0) >= self._msg_flush_interval:
                    await self._flush_buffer(session_id)

    def start(self) -> None:
        """Start background flush task (call once at app startup)."""
        if self._flush_task is not None and not self._flush_task.done():
            return
        self._flush_task = _spawn(self._periodic_flush())

    async def stop(self) -> None:
        """Stop background flush task (call at app shutdown)."""
        if self._flush_task is not None:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        for session_id in list(self._msg_buffers.keys()):
            await self._flush_buffer(session_id)
