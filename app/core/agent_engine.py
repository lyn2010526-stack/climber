"""Agent engine facade with ReAct loop.

The AgentEngine class orchestrates agent execution with tool validation,
streaming, and checkpoint management. Implementation details live in
``app.core.engine.*`` submodules; this facade keeps every historical
override point (``_validate_tool_call``, ``_save_checkpoint``,
``_persist_message``, ``_make_parallel_executor``, notification and memory
hooks) so tests and subclasses can intercept them from one place.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import sys
from collections.abc import AsyncIterator
from typing import Any

from anyio import CancelScope

from app.core import (
    AgentEvent,
    AgentEventType,
    ChatResult,
    ContextConfig,
    MessageRole,
)
from app.core.checkpoint import InMemoryCheckpointStore, SQLiteCheckpointStore
from app.core.di import resolve as di_resolve
from app.core.engine.bootstrap import (
    init_debug_loop,
    init_permissions,
    init_reasoning,
    init_sandbox,
    load_permission_config,
    permission_config_path,
    save_permission_config,
    setup_default_permissions,
)
from app.core.engine.dual_loop_hooks import (
    current_reasoning_level,
    dual_loop_coordinator,
    last_tool_name,
    metacognition_enabled,
    metacognition_orchestrator,
)
from app.core.engine.iteration import save_checkpoint
from app.core.engine.llm_calls import (
    accumulate_stream_tool_calls,
    call_llm,
    call_llm_with_resilience,
    stream_accumulate,
    stream_chat,
)
from app.core.engine.memory_hooks import (
    archive_instruction,
    inject_core_memory,
    inject_memory_context,
    set_agent_mode,
    store_episodic_memory,
    trigger_memory_reflection,
)
from app.core.engine.notifications import (
    send_completion_notification,
    send_failure_notification,
    send_start_notification,
)

# Patch targets used by tests: tests patch these names on this facade module,
# and the thin engine methods below resolve them at call time.
from app.core.engine.persistence import persist_message
from app.core.engine.run_storage import RunStorage, track_run
from app.core.engine.runner import (
    TASK_MEMORY_MARKER,
    handle_text_result,
    iteration_loop,
    run_locked,
)
from app.core.engine.session_runner import (  # noqa: F401
    merge_stream_chunk,
    response_usage,
)
from app.core.engine.tool_exec import handle_tool_debug, handle_tool_execution
from app.core.engine.tools import build_tools
from app.core.engine.validation import (  # noqa: F401
    _COMMAND_TOOLS,
    _FILE_TOOLS,
    _approval_key,
    validate_tool_call,
)
from app.core.parallel import ParallelToolExecutor
from app.core.persistent_memory import PersistentMemoryService
from app.core.resilience import ResourceTracker
from app.core.session import AgentSession, SessionConfig
from app.core.tool_prioritizer import ToolPrioritizer
from app.models.registry import ModelRegistry
from app.models.vision import ChatAttachment
from app.tools import ToolRegistry


def _follow_up_hash(message: str) -> str:
    """Deterministic short hash for agent self-continue follow-up dedupe."""
    return hashlib.sha256(message.encode("utf-8")).hexdigest()[:12]


def _outer_turn_signature(session: Any) -> tuple:
    """Per-turn overall-progress signature for the Pi outer-loop stall guard.

    Progress means a new assistant output (different last assistant content) or
    a state transition. Two stalled turns share the same signature; any new
    distinct assistant output changes it.
    """
    last_assistant: str | None = None
    for msg in reversed(getattr(session, "messages", []) or []):
        if msg.get("role") == MessageRole.ASSISTANT:
            content = msg.get("content")
            if isinstance(content, str) and content.strip():
                last_assistant = content
            break
    return (session.status.value, last_assistant)


def _outer_stall_update(signature: tuple, previous: tuple | None, count: int) -> tuple[int, tuple]:
    """Update the consecutive stall counter; returns (count, latest_signature)."""
    if previous is not None and signature == previous:
        return count + 1, signature
    return 0, signature


def _resolve_registry(service_name: str, factory: Any) -> Any:
    """Resolve a registry from DI, falling back to a fresh instance.

    Args:
        service_name: The DI service name to resolve.
        factory: Zero-arg factory used when DI resolution fails.

    Returns:
        The resolved registry instance.
    """
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
        """Initialize the engine with registries, services and sub-hooks.

        Args:
            model_registry: Optional model registry (DI-resolved when absent).
            tool_registry: Optional tool registry (DI-resolved when absent).
            checkpoint_store: Optional checkpoint store (SQLite when absent).
            run_store: Optional run storage (fresh RunStorage when absent).

        Returns:
            None
        """
        self.model_registry = model_registry or _resolve_registry("ModelRegistry", ModelRegistry)
        self.tool_registry = tool_registry or _resolve_registry("ToolRegistry", ToolRegistry)
        self._checkpoints = (
            checkpoint_store if checkpoint_store is not None else SQLiteCheckpointStore()
        )
        self._run_store = run_store if run_store is not None else RunStorage()
        from app.core.engine.input_queue import SessionInputQueue

        self._input_queue = SessionInputQueue(self._run_store.session_factory)
        self._sessions: dict[str, AgentSession] = {}
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._background_tasks: set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()
        self.resource_tracker = ResourceTracker()
        self.memory_service = PersistentMemoryService()
        self.tool_prioritizer = ToolPrioritizer()
        self._dual_loop: Any = None
        self._metacognition: Any = None
        self.reasoning = None
        self._init_debug_loop()
        self._init_sandbox()
        self._init_permissions()
        self._init_reasoning()

    # --- bootstrap hooks (patch points used by tests and subclasses) ---

    def _init_reasoning(self) -> None:
        """Initialize the multi-strategy reasoning service so the /reason API works."""
        init_reasoning(self)

    def _init_debug_loop(self) -> None:
        """Debug loop extension point; wired when a debug engine is installed."""
        init_debug_loop(self)

    def _init_sandbox(self) -> None:
        """Initialize the security sandbox, degrading to no sandbox on failure."""
        init_sandbox(self)

    def _init_permissions(self) -> None:
        """Initialize default permission configuration, reloading persisted config."""
        init_permissions(self)

    @staticmethod
    def _permission_config_path() -> str:
        """Return the filesystem path of the persisted permission config."""
        return permission_config_path()

    def _load_permission_config(self) -> Any:
        """Load the persisted default permission config, if any."""
        return load_permission_config()

    def _save_permission_config(self, config: Any) -> None:
        """Persist the default permission config so it survives restarts."""
        save_permission_config(config)

    def _setup_default_permissions(self) -> None:
        """Setup default permission overlay, mirroring permission_rules DEFAULT mode."""
        setup_default_permissions(self)

    # --- session management ---

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
        temperature: float | None = None,
        max_tokens: int | None = None,
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
            temperature: Optional per-session sampling temperature override;
                forwarded to the model adapter on every LLM call.
            max_tokens: Optional per-session generation token cap override;
                forwarded to the model adapter on every LLM call.

        Returns:
            The created AgentSession instance.
        """
        from uuid import uuid4

        sid = session_id or str(uuid4())
        # Only pass sampling overrides when explicitly set so they do not
        # clobber values already carried by ``session_config``.
        sampling_overrides: dict[str, Any] = {}
        if temperature is not None:
            sampling_overrides["temperature"] = temperature
        if max_tokens is not None:
            sampling_overrides["max_tokens"] = max_tokens
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
            **sampling_overrides,
        )
        if (
            hasattr(self, "_default_permission_config")
            and self._default_permission_config is not None
        ):
            session.permission_config = self._default_permission_config
        if system_prompt:
            session.messages.append({"role": MessageRole.SYSTEM, "content": system_prompt})
        self._sessions[sid] = session
        return session

    def close_session(self, session: AgentSession | str) -> None:
        """Remove a session from the in-memory registry.

        One-shot callers (e.g. workflow sub-agent LLM calls) must release
        sessions they create so the registry does not grow without bound.

        Args:
            session: The session instance or its session ID.
        """
        sid = session if isinstance(session, str) else getattr(session, "session_id", None)
        if sid:
            self._sessions.pop(sid, None)

    async def run(
        self,
        session: AgentSession,
        message: str,
        images: list[str] | None = None,
        attachments: list[ChatAttachment] | None = None,
        *,
        queued_only: bool = False,
    ) -> AsyncIterator[AgentEvent]:
        """Run the agent engine for a session and message.

        Concurrent runs on the same session are rejected with a busy error
        while a previous run still holds the session lock; the busy path
        never releases or removes that lock.

        Args:
            session: The agent session.
            message: The user message.
            images: Optional image references (base64 data URLs or http(s)
                URLs); when present the user message is built as OpenAI
                vision content parts.
            attachments: Optional chat attachments.

        Yields:
            AgentEvent instances during execution.
        """
        lock = self._session_locks.get(session.session_id)
        if lock is not None and lock.locked():
            yield AgentEvent(
                type=AgentEventType.ERROR,
                data={"error": "Session is busy processing another request"},
            )
            return
        if lock is None:
            lock = self._session_locks.setdefault(session.session_id, asyncio.Lock())
            if lock.locked():
                yield AgentEvent(
                    type=AgentEventType.ERROR,
                    data={"error": "Session is busy processing another request"},
                )
                return

        try:
            async with lock:
                input_id = None
                first = True
                if queued_only:
                    from app.core.engine.input_dispatch import prepare_dispatch

                    item = await prepare_dispatch(
                        self._input_queue,
                        session.session_id,
                        session.user_id,
                        claim=True,
                        session=session,
                    )
                    input_id, message, first = item["id"], item["message"], False
                    yield AgentEvent(type=AgentEventType.INPUT_STATUS, data={"item": item})
                outer_no_progress = 0
                outer_prev_signature = None
                outer_rounds = 0
                completed_subtasks: list[str] = []
                while True:
                    session._continuing_input = not first
                    if not first and session._stop_requested:
                        for item in await self._input_queue.freeze(
                            session.session_id, session.user_id, "Execution stopped"
                        ):
                            yield AgentEvent(type=AgentEventType.INPUT_STATUS, data={"item": item})
                        yield AgentEvent(
                            type=AgentEventType.RUNTIME_REPORT,
                            data=await self._input_queue.report(
                                session.session_id,
                                session.user_id,
                            ),
                        )
                        yield AgentEvent(type=AgentEventType.DONE, data={"status": "stopped"})
                        break
                    terminal = []
                    async with self._track_run_with_cleanup(session):
                        if first:
                            recovered = await self._input_queue.recover(
                                session.session_id, session.user_id
                            )
                            for item in recovered:
                                yield AgentEvent(
                                    type=AgentEventType.INPUT_STATUS, data={"item": item}
                                )
                            if recovered:
                                raise RuntimeError(
                                    "Interrupted input has unknown effects; manual review required"
                                )
                        outer_rounds += 1
                        session._outer_rounds = outer_rounds
                        yield AgentEvent(
                            type=AgentEventType.TURN_STARTED,
                            data={"input_id": input_id, "message": message},
                        )
                        yield AgentEvent(
                            type=AgentEventType.RUNTIME_REPORT,
                            data=await self._input_queue.report(
                                session.session_id,
                                session.user_id,
                                message if input_id is None else None,
                            ),
                        )
                        async with contextlib.aclosing(
                            self._run_locked(session, message, images, attachments)
                        ) as events:
                            async for event in events:
                                if event.type in {AgentEventType.DONE, AgentEventType.ERROR}:
                                    terminal.append(event)
                                else:
                                    yield event
                                    if event.type == AgentEventType.INPUT_STATUS:
                                        yield AgentEvent(
                                            type=AgentEventType.RUNTIME_REPORT,
                                            data=await self._input_queue.report(
                                                session.session_id,
                                                session.user_id,
                                                message if input_id is None else None,
                                            ),
                                        )
                    # The turn transaction is committed before acknowledging or claiming inputs.
                    yield AgentEvent(
                        type=AgentEventType.TURN_DONE,
                        data={
                            "input_id": input_id,
                            "turn_id": session.current_turn_id,
                            "status": getattr(session, "_run_status_override", None)
                            or session.status.value,
                            "message_id": getattr(session, "_last_assistant_message_id", None),
                        },
                    )
                    if (
                        getattr(session, "_run_status_override", None)
                        or session.status.value == "completed"
                    ) and message not in completed_subtasks:
                        completed_subtasks.append(message)
                    loop_payload: dict[str, Any] = {
                        "outer_round": outer_rounds,
                        "current_input": message,
                        "completed": completed_subtasks,
                        "followup_queue": [],
                        "steering_queue": [],
                        "no_progress_count": outer_no_progress,
                    }
                    try:
                        for queued_item in await self._input_queue.list(
                            session.session_id, session.user_id
                        ):
                            if queued_item["status"] not in {"queued", "started"}:
                                continue
                            target = (
                                loop_payload["followup_queue"]
                                if queued_item["kind"] == "follow_up"
                                else loop_payload["steering_queue"]
                            )
                            target.append(queued_item["message"])
                    except LookupError:
                        pass
                    yield AgentEvent(type=AgentEventType.LOOP_STATUS, data=loop_payload)
                    try:
                        from app.core.engine.run_progress import record_loop_progress

                        await record_loop_progress(self, session, loop_payload)
                    except BaseException:
                        pass
                    if input_id:
                        stopped = session._stop_requested or session.status.value in {
                            "paused",
                            "stopped",
                            "cancelled",
                        }
                        finish_status = (
                            "blocked"
                            if stopped
                            else "completed"
                            if session.status.value == "completed"
                            else "failed"
                        )
                        finish_error = session._last_error
                        if finish_error is None and finish_status != "completed":
                            finish_error = (
                                "Execution stopped before the input completed"
                                if stopped
                                else "Input ended without a recorded error"
                            )
                        item = await self._input_queue.finish(
                            session.session_id,
                            session.user_id,
                            input_id,
                            finish_status,
                            finish_error,
                        )
                        yield AgentEvent(type=AgentEventType.INPUT_STATUS, data={"item": item})
                    pi_auto = bool(
                        (getattr(session, "context", None) or {}).get("pi_auto_continue")
                    )
                    if (
                        pi_auto
                        and session.max_iterations
                        and outer_rounds >= session.max_iterations
                    ):
                        reason = "Outer loop reached max iterations; pausing auto-continue"
                        session._last_error = reason
                        session._run_status_override = "max_iterations_reached"
                        for item in await self._input_queue.freeze(
                            session.session_id, session.user_id, reason
                        ):
                            yield AgentEvent(type=AgentEventType.INPUT_STATUS, data={"item": item})
                        yield AgentEvent(
                            type=AgentEventType.RUNTIME_REPORT,
                            data=await self._input_queue.report(
                                session.session_id,
                                session.user_id,
                            ),
                        )
                        yield AgentEvent(
                            type=AgentEventType.PROGRESS,
                            data={"status": "paused", "reason": reason},
                        )
                        yield AgentEvent(
                            type=AgentEventType.DONE,
                            data={"status": "max_iterations_reached", "error": reason},
                        )
                        break
                    if session._stop_requested or session.status.value != "completed":
                        reason = (
                            session._last_error or "Execution stopped; queued inputs require review"
                        )
                        for item in await self._input_queue.freeze(
                            session.session_id, session.user_id, reason
                        ):
                            yield AgentEvent(type=AgentEventType.INPUT_STATUS, data={"item": item})
                        yield AgentEvent(
                            type=AgentEventType.RUNTIME_REPORT,
                            data=await self._input_queue.report(
                                session.session_id,
                                session.user_id,
                            ),
                        )
                        for event in terminal:
                            if event.type == AgentEventType.DONE and session._stop_requested:
                                event = AgentEvent(
                                    type=AgentEventType.DONE,
                                    data={**event.data, "status": "stopped"},
                                )
                            yield event
                        if not any(event.type == AgentEventType.DONE for event in terminal):
                            yield AgentEvent(
                                type=AgentEventType.DONE,
                                data={
                                    "status": getattr(session, "_run_status_override", None)
                                    or session.status.value,
                                    "error": session._last_error,
                                },
                            )
                        break
                    # Pi outer loop: stall guard over the follow-up queue.
                    # Two consecutive turns without overall progress (no new
                    # iteration, no new output) pause the outer loop and dump state.
                    turn_signature = _outer_turn_signature(session)
                    outer_no_progress, outer_prev_signature = _outer_stall_update(
                        turn_signature, outer_prev_signature, outer_no_progress
                    )
                    if outer_no_progress >= 2:
                        reason = "Agent produced two consecutive turns without overall progress; pausing outer loop"
                        session._last_error = reason
                        session._run_status_override = "no_progress"
                        for item in await self._input_queue.freeze(
                            session.session_id, session.user_id, reason
                        ):
                            yield AgentEvent(type=AgentEventType.INPUT_STATUS, data={"item": item})
                        yield AgentEvent(
                            type=AgentEventType.RUNTIME_REPORT,
                            data=await self._input_queue.report(
                                session.session_id,
                                session.user_id,
                            ),
                        )
                        yield AgentEvent(
                            type=AgentEventType.PROGRESS,
                            data={"status": "paused", "reason": reason},
                        )
                        for event in terminal:
                            if event.type != AgentEventType.DONE:
                                yield event
                        yield AgentEvent(
                            type=AgentEventType.DONE,
                            data={
                                "status": "no_progress",
                                "error": reason,
                            },
                        )
                        break
                    item = await self._input_queue.claim(
                        session.session_id, session.user_id, "follow_up"
                    )
                    if item is None:
                        yield AgentEvent(
                            type=AgentEventType.RUNTIME_REPORT,
                            data=await self._input_queue.report(
                                session.session_id,
                                session.user_id,
                            ),
                        )
                        for event in terminal:
                            yield event
                        break
                    input_id, message = item["id"], item["message"]
                    images, attachments, first = None, None, False
                    yield AgentEvent(type=AgentEventType.INPUT_STATUS, data={"item": item})
        except BaseException:
            with CancelScope(shield=True):
                await self._input_queue.freeze(
                    session.session_id,
                    session.user_id,
                    "Execution interrupted; manual review required",
                )
            raise
        finally:
            session._continuing_input = False
            try:
                from app.core.engine.run_progress import finalize_run_progress

                with CancelScope(shield=True):
                    await finalize_run_progress(self, session)
            except BaseException:
                pass
            if self._session_locks.get(session.session_id) is lock:
                self._session_locks.pop(session.session_id, None)

    @contextlib.asynccontextmanager
    async def _track_run_with_cleanup(self, session: AgentSession):
        manager = track_run(session, self._run_store)
        await manager.__aenter__()
        try:
            yield
        except BaseException:
            # SSE disconnect uses level cancellation; durable cleanup must survive it.
            with CancelScope(shield=True):
                suppressed = await manager.__aexit__(*sys.exc_info())
                await self._summarize_task_memory(session)
            if not suppressed:
                raise
        else:
            with CancelScope(shield=True):
                await manager.__aexit__(None, None, None)
                await self._summarize_task_memory(session)

    def run_inputs(self, session: AgentSession) -> AsyncIterator[AgentEvent]:
        """Explicitly execute safe queued tasks without inventing a chat message."""
        return self.run(session, "", queued_only=True)

    async def run_agent(self, session: AgentSession, message: str) -> dict[str, Any]:
        """Consume the streaming API and return the legacy aggregate result.

        Args:
            session: The agent session.
            message: The user message.

        Returns:
            A dict with output, tokens_used, status, error and cost status.
        """
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
        return {
            "output": "".join(output_parts),
            "tokens_used": getattr(session, "_run_tokens", tokens_used),
            "status": status or session.status.value,
            "error": error,
            "cost_status": cost_status,
            "usage_status": getattr(session, "_run_usage_status", "unknown"),
        }

    # --- execution loop entry points (async-generator valued) ---

    async def _consume_steering(self, session: AgentSession) -> AsyncIterator[AgentEvent]:
        queue = getattr(self, "_input_queue", None)
        if queue is None:
            return
        while not session._stop_requested:
            item = await queue.claim(session.session_id, session.user_id, "steering")
            if item is None:
                break
            yield AgentEvent(type=AgentEventType.INPUT_STATUS, data={"item": item})
            if session._stop_requested:
                item = await self._input_queue.finish(
                    session.session_id, session.user_id, item["id"], "blocked", "Execution stopped"
                )
                yield AgentEvent(type=AgentEventType.INPUT_STATUS, data={"item": item})
                break
            session.messages.append({"role": MessageRole.USER, "content": item["message"]})
            persisted = await self._persist_message(
                session.session_id, MessageRole.USER, content=item["message"]
            )
            if not persisted:
                raise RuntimeError("Steering message persistence failed")
            await self._save_checkpoint(session, {"steering_input_id": item["id"]})
            item = await self._input_queue.finish(
                session.session_id, session.user_id, item["id"], "applied"
            )
            yield AgentEvent(type=AgentEventType.INPUT_STATUS, data={"item": item})

    async def _enqueue_follow_up(self, session: AgentSession, message: str) -> str:
        """Pi dual-loop: agent enqueues its own next subtask for auto-continue.

        Deduped by (session_id, client_request_id); the id derives from the
        session id and a stable hash of the message, so re-enqueueing the same
        subtask keeps only one row.
        """
        client_request_id = f"agent-followup:{_follow_up_hash(message)}"
        item = await self._input_queue.submit(
            session.session_id,
            session.user_id,
            client_request_id,
            "follow_up",
            message,
        )
        return str(item["id"])

    async def _decide_followup(
        self, session: AgentSession, result: Any
    ) -> dict[str, str | bool | None]:
        """Pi dual-loop G1 default decider: one light LLM call, no context pollution.

        Asks the model to return ``{"finished": bool, "next_subtask": str|None,
        "reason": str}``. Never appends to the main message chain and never
        touches the file system; anything unparsable means "finished".
        """
        from app.core.engine.session_runner import run_llm_single

        evidence = ""
        if result is not None:
            evidence = result.accumulated_content or result.content or ""
        prompt = (
            "Continue deciding for a long-running task. The current turn ended with:\n"
            f"{evidence[:4000]}\n\n"
            'Return ONLY JSON: {"finished": true} when the task is done, or '
            '{"finished": false, "next_subtask": "<one concrete next step>", "reason": "<why>"}.'
        )
        system = "You are an outer-loop controller. Decide if another subtask should run."
        raw = await run_llm_single(
            self,
            session.provider,
            session.model_id,
            session.api_key,
            system,
            prompt,
            base_url=session.base_url,
            max_chars=2000,
        )
        try:
            import json

            decision = json.loads(raw[raw.find("{") : raw.rfind("}") + 1] or "{}")
            if not isinstance(decision, dict):
                raise ValueError("decision is not an object")
        except (ValueError, TypeError):
            return {"finished": True, "next_subtask": None, "reason": "unparsable decision"}
        finished = bool(decision.get("finished", True))
        next_subtask = decision.get("next_subtask")
        if finished or not (isinstance(next_subtask, str) and next_subtask.strip()):
            return {
                "finished": finished,
                "next_subtask": None,
                "reason": decision.get("reason", "finished" if finished else "empty subtask"),
            }
        return {
            "finished": False,
            "next_subtask": next_subtask.strip(),
            "reason": decision.get("reason", ""),
        }

    async def maybe_generate_followup(
        self, session: AgentSession, result: Any
    ) -> dict[str, str | bool | None] | None:
        """Pi dual-loop G1 gate: decide and enqueue the next auto-continue subtask.

        Opt-in only (``session.context["pi_auto_continue"]``). Skipped while
        stopped, frozen, or at the outer round cap. Returns the decision dict,
        or ``None`` when no decision should be requested.
        """
        context = getattr(session, "context", None) or {}
        if not context.get("pi_auto_continue"):
            return None
        if session._stop_requested or (context or {}).get("input_queue_frozen"):
            return None
        outer_rounds = int(getattr(session, "_outer_rounds", 0) or 0)
        max_rounds = int(getattr(session, "max_iterations", 0) or 0)
        if max_rounds and outer_rounds >= max_rounds:
            return None
        decision = await self._decide_followup(session, result)
        if decision is not None and not decision.get("finished") and decision.get("next_subtask"):
            await self._enqueue_follow_up(session, str(decision["next_subtask"]))
        return decision

    def _run_locked(
        self,
        session: AgentSession,
        message: str,
        images: list[str] | None = None,
        attachments: list[ChatAttachment] | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Internal run method - executes under session lock."""
        return run_locked(self, session, message, images, attachments)

    def _iteration_loop(
        self,
        session: AgentSession,
        executor: Any,
        compressor: Any,
    ) -> AsyncIterator[AgentEvent]:
        """Main iteration loop for agent execution."""
        return iteration_loop(self, session, executor, compressor)

    def _handle_text_result(
        self, session: AgentSession, result: Any, adapter: Any
    ) -> AsyncIterator[AgentEvent]:
        """Handle text content from LLM response."""
        return handle_text_result(self, session, result, adapter)

    def _handle_tool_execution(
        self,
        session: AgentSession,
        executor: Any,
        result: Any,
        iteration: int,
        ctx_tokens: int,
        metacognition: Any = None,
    ) -> AsyncIterator[AgentEvent]:
        """Handle tool execution from LLM response."""
        return handle_tool_execution(
            self, session, executor, result, iteration, ctx_tokens, metacognition=metacognition
        )

    # --- override points routed to engine submodules ---

    async def _save_checkpoint(
        self,
        session: AgentSession,
        channels: dict[str, Any],
        pending_writes: list[dict[str, Any]] | None = None,
    ) -> str:
        """Persist a sanitized checkpoint snapshot of the session.

        Args:
            session: The agent session to snapshot.
            channels: Channel values to store alongside the checkpoint.
            pending_writes: Optional pending writes to attach.

        Returns:
            The checkpoint id assigned by the checkpoint store.
        """
        return await save_checkpoint(self._checkpoints, session, channels, pending_writes)

    async def _call_llm(
        self, adapter: Any, session: AgentSession, tools: list
    ) -> ChatResult | None:
        """Call the LLM adapter and return the result.

        Args:
            adapter: The LLM adapter.
            session: The current session.
            tools: Available tool definitions.

        Returns:
            ChatResult or None if stopped.
        """
        return await call_llm(adapter, session, tools)

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
        return await call_llm_with_resilience(self, session, model_adapter, messages, iteration)

    async def _stream_accumulate(
        self, adapter: Any, messages: list[dict[str, Any]], tools: list
    ) -> ChatResult:
        """Accumulate a streaming response into a single ChatResult.

        Args:
            adapter: The LLM adapter with a ``stream_chat`` method.
            messages: The messages to send.
            tools: Available tool definitions.

        Returns:
            A ChatResult with accumulated content and tool calls.
        """
        return await stream_accumulate(adapter, messages, tools)

    async def _stream_chat(
        self, adapter: Any, session: AgentSession, tools: list
    ) -> ChatResult | None:
        """Handle streaming chat response for a session.

        Args:
            adapter: The LLM adapter.
            session: The current session.
            tools: Available tool definitions.

        Returns:
            ChatResult with accumulated content, or None if stopped.
        """
        return await stream_chat(adapter, session, tools)

    @staticmethod
    def _accumulate_stream_tool_calls(
        accumulated: list[dict[str, Any]], chunks: list[dict[str, Any]]
    ) -> None:
        """Merge streamed tool call deltas into complete tool calls.

        Args:
            accumulated: The list of accumulated tool calls (mutated in place).
            chunks: The streamed tool call deltas to merge.
        """
        accumulate_stream_tool_calls(accumulated, chunks)

    def _validate_tool_call(
        self, session: AgentSession, tool_name: str, arguments: dict[str, Any]
    ) -> tuple[bool, str]:
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
        """Build OpenAI-style tool definitions for the given tool names.

        Args:
            tool_names: The tool names to include.

        Returns:
            A list of tool definition dictionaries.
        """
        return build_tools(self.tool_registry, list(tool_names or []), self.tool_prioritizer)

    def _build_tools_for_session(
        self, session: AgentSession, task_description: str = ""
    ) -> list[dict[str, Any]]:
        """Build tool definitions for the session's enabled tools.

        Args:
            session: The agent session providing the enabled tool names.
            task_description: Task description for context-aware ranking.

        Returns:
            A list of tool definition dictionaries.
        """
        return build_tools(
            self.tool_registry,
            session.tools,
            self.tool_prioritizer,
            task_description=task_description,
        )

    def _make_parallel_executor(self, session: AgentSession) -> ParallelToolExecutor:
        """Build the parallel tool executor bound to the facade validation.

        The validator delegates to ``self._validate_tool_call`` so the facade
        override point stays authoritative for every executed tool call.

        Args:
            session: The agent session the executor runs for.

        Returns:
            A ParallelToolExecutor bound to the session.
        """
        return ParallelToolExecutor(
            self.tool_registry,
            validator=(lambda name, args: self._validate_tool_call(session, name, args)),
            session=session,
        )

    async def _persist_message(self, *args: Any, **kwargs: Any) -> str | None:
        """Persist a message through the patchable module-level hook.

        Args:
            *args: Positional arguments forwarded to ``persist_message``.
            **kwargs: Keyword arguments forwarded to ``persist_message``.

        Returns:
            The persisted message id, or None when persistence failed.
        """
        return await persist_message(*args, **kwargs)

    async def _handle_tool_debug(self, session: AgentSession, tr: Any) -> None:
        """Handle debug recovery for failed tool calls.

        Args:
            session: The current session.
            tr: The tool result to check for errors.
        """
        await handle_tool_debug(self, session, tr)

    def _set_agent_mode(self, session: AgentSession) -> None:
        """Set the current agent mode for tool execution context.

        Args:
            session: The agent session.
        """
        set_agent_mode(session)

    def _send_start_notification(self, session: AgentSession) -> None:
        """Send notification when agent starts.

        Args:
            session: The agent session.
        """
        send_start_notification(self, session)

    def _send_completion_notification(self, session: AgentSession, result: Any) -> None:
        """Send notification when agent completes.

        Args:
            session: The agent session.
            result: The final ChatResult.
        """
        send_completion_notification(self, session, result)

    def _send_failure_notification(self, session: AgentSession, error: str) -> None:
        """Send notification when agent fails.

        Args:
            session: The agent session.
            error: The error message.
        """
        send_failure_notification(self, session, error)

    def _spawn(self, coro: Any) -> None:
        """Run a fire-and-forget task while holding a reference until it finishes.

        Args:
            coro: The coroutine to schedule.
        """
        try:
            task = asyncio.create_task(coro)
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        except Exception:
            close = getattr(coro, "close", None)
            if callable(close):
                close()

    async def _inject_memory_context(self, session: AgentSession, message: str) -> None:
        """Inject relevant memories into session context.

        Args:
            session: The agent session.
            message: The user query for memory retrieval.
        """
        await inject_memory_context(self, session, message)

    async def _inject_task_memory_context(
        self, session: AgentSession, *, token_budget: int = 2048
    ) -> None:
        """Refresh a bounded durable task view without splitting tool exchanges."""
        import structlog

        from app.core.engine.task_memory import TaskMemory

        session.messages = [
            msg
            for msg in session.messages
            if not (
                msg.get("role") == MessageRole.SYSTEM
                and isinstance(msg.get("content"), str)
                and msg["content"].startswith(TASK_MEMORY_MARKER)
            )
        ]
        try:
            budget = min(2048, max(0, token_budget), max(0, session.context_config.max_tokens // 4))
            prefix = TASK_MEMORY_MARKER + "\n"
            view = await TaskMemory(self._run_store.session_factory).restore(
                session.session_id,
                session.user_id,
                token_budget=max(0, budget - len(prefix.encode("utf-8"))),
            )
            session.task_memory_diagnostics = {
                "status": "restored",
                "budget_used": view["budget_used"],
                "omitted": view["omitted"],
            }
            if view["task_context"]:
                position = 0
                while (
                    position < len(session.messages)
                    and session.messages[position].get("role") == MessageRole.SYSTEM
                ):
                    position += 1
                session.messages.insert(
                    position, {"role": MessageRole.SYSTEM, "content": prefix + view["task_context"]}
                )
        except Exception as exc:
            session.task_memory_diagnostics = {"status": "restore_failed", "error": str(exc)}
            structlog.get_logger().warning(
                "task_memory_restore_failed",
                session_id=session.session_id,
                turn_id=session.current_turn_id,
                error=str(exc),
            )

    async def _summarize_task_memory(self, session: AgentSession) -> None:
        """Summarize committed outcomes under the existing session lock."""
        import structlog

        from app.core.engine.task_memory import TaskMemory

        try:
            summary = await TaskMemory(self._run_store.session_factory).summarize_turn(
                session.session_id,
                session.user_id,
                session.current_turn_id,
            )
            session.task_memory_summary_diagnostics = {
                "status": "stored",
                "revision": summary["revision"],
                "source_hash": summary["source_hash"],
            }
        except Exception as exc:
            session.task_memory_summary_diagnostics = {
                "status": "summary_failed",
                "error": str(exc),
            }
            structlog.get_logger().warning(
                "task_memory_summary_failed",
                session_id=session.session_id,
                turn_id=session.current_turn_id,
                error=str(exc),
            )

    async def _archive_instruction(self, session: AgentSession, message: str) -> None:
        """Persist the verbatim instruction and its safe local parse.

        Args:
            session: The agent session.
            message: The user instruction of this run.
        """
        await archive_instruction(session, message)

    async def _inject_core_memory(self, session: AgentSession) -> None:
        """Inject core memory blocks into session context.

        Args:
            session: The agent session.
        """
        await inject_core_memory(session)

    async def _store_episodic_memory(self, session: AgentSession, message: str) -> None:
        """Store important interaction in episodic memory.

        Args:
            session: The agent session.
            message: The user message.
        """
        await store_episodic_memory(self, session, message)

    def _trigger_memory_reflection(self, session: AgentSession) -> None:
        """Trigger memory reflection (fire-and-forget).

        Args:
            session: The agent session.
        """
        trigger_memory_reflection(self, session)

    # --- dual-loop and metacognition wiring ---

    def _dual_loop_coordinator(self) -> Any:
        """Lazily build the dual-loop coordinator; None when unavailable.

        Returns:
            The DualLoopCoordinator instance, or None if the module cannot
            be imported or constructed.
        """
        return dual_loop_coordinator(self)

    @property
    def metacognition(self) -> Any:
        """Lazily build the metacognition orchestrator; None when unavailable.

        Returns:
            MetacognitionOrchestrator instance, or None when the subsystem
            cannot be imported. The orchestrator stays advisory in the main
            loop, so a failure here never blocks a normal agent run.
        """
        return metacognition_orchestrator(self)

    @property
    def metacognition_enabled(self) -> bool:
        """Whether the main loop should run the metacognition stage."""
        return metacognition_enabled(self)

    async def _inject_profile_context(self, session: AgentSession, message: str) -> None:
        """Inject the user-profile context into session context (dual loop 1).

        Args:
            session: The agent session.
            message: The user query the profile is adapted to.
        """
        from app.core.engine.dual_loop_hooks import inject_profile_context

        await inject_profile_context(self, session, message)

    def _record_profile_outcome(self, session: AgentSession, message: str) -> None:
        """Feed the finished run back into the user profile (fire-and-forget).

        Args:
            session: The agent session.
            message: The user instruction of this run.
        """
        from app.core.engine.dual_loop_hooks import record_profile_outcome

        record_profile_outcome(self, session, message)

    def _tick_evolution(self, session: AgentSession) -> None:
        """Advance the genetic evolution tick counter (fire-and-forget).

        Args:
            session: The agent session.
        """
        from app.core.engine.dual_loop_hooks import tick_evolution

        tick_evolution(self, session)

    @staticmethod
    def _current_reasoning_level(session: AgentSession) -> str:
        """Read this run's reasoning level, falling back to "standard".

        Args:
            session: The agent session.

        Returns:
            The configured reasoning level string.
        """
        return current_reasoning_level(session)

    @staticmethod
    def _last_tool_name(session: AgentSession) -> str | None:
        """Name of the last tool executed in this run, or None.

        Args:
            session: The agent session.

        Returns:
            The last tool name found in the message history.
        """
        return last_tool_name(session)

    # --- lifecycle ---

    async def graceful_shutdown(self) -> None:
        """Gracefully shut down the engine and all tracked sessions."""
        self._shutdown_event.set()
        for session in list(self._sessions.values()):
            with contextlib.suppress(Exception):
                await session.graceful_shutdown()
        await self.resource_tracker.cleanup()

    async def recover_session(self, session: AgentSession) -> bool:
        """Attempt to recover a session from a saved checkpoint.

        Args:
            session: The session to recover.

        Returns:
            True if a checkpoint was found and loaded, False otherwise.
        """
        from app.core.recovery import RecoveryManager

        return await RecoveryManager(self._checkpoints).restore_session(session)

    async def __aenter__(self) -> AgentEngine:
        """Enter the engine context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the engine context manager, marking shutdown."""
        self._shutdown_event.set()

    # --- permission API ---

    def resolve_permission(
        self, tool_call_id: str, decision: str, *, owner_id: str | None = None
    ) -> bool:
        """Resolve a pending permission request.

        Args:
            tool_call_id: The ID of the tool call awaiting permission.
            decision: One of 'allow', 'allow_session', 'allow_always', 'deny'.

        Returns:
            True if the permission was resolved, False if no pending request found.
        """
        for session in self._sessions.values():
            if owner_id is not None and session.user_id != owner_id:
                continue
            if (
                session._pending_permission
                and session._pending_permission.get("tool_call_id") == tool_call_id
            ):
                session._pending_permission["decision"] = decision
                if session._permission_event is not None:
                    session._permission_event.set()
                return True
        return False

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
