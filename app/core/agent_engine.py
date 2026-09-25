"""Minimal agent engine with ReAct loop.

This module provides the AgentEngine class that orchestrates agent execution
with tool validation, streaming, and checkpoint management.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
import time
from collections.abc import AsyncIterator
from typing import Any

from app.core import (
    AgentEvent,
    AgentEventType,
    ChatResult,
    ContextConfig,
    MessageRole,
)
from app.core.checkpoint import InMemoryCheckpointStore, SQLiteCheckpointStore
from app.core.compressor import ContextCompressor, estimate_tokens
from app.core.di import resolve as di_resolve
from app.core.engine.persistence import persist_message
from app.core.engine.run_storage import RunStorage, track_run
from app.core.engine.session_runner import merge_stream_chunk, response_usage
from app.core.engine.tools import build_tools
from app.core.engine.validation import (
    _COMMAND_TOOLS,
    _FILE_TOOLS,
    _approval_key,
    validate_tool_call,
)
from app.core.parallel import ParallelToolExecutor
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
        self._checkpoints = checkpoint_store if checkpoint_store is not None else SQLiteCheckpointStore()
        self._run_store = run_store if run_store is not None else RunStorage()
        self._sessions: dict[str, AgentSession] = {}
        self._session_locks: dict[str, asyncio.Lock] = {}
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
        except Exception:
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
        except Exception:
            pass

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
        self._sessions[sid] = session
        return session

    async def run(self, session: AgentSession, message: str) -> AsyncIterator[AgentEvent]:
        """Run the agent engine for a session and message.

        Args:
            session: The agent session.
            message: The user message.

        Yields:
            AgentEvent instances during execution.
        """
        if session.session_id not in self._session_locks:
            self._session_locks[session.session_id] = asyncio.Lock()

        lock = self._session_locks[session.session_id]
        if lock.locked():
            yield AgentEvent(type=AgentEventType.ERROR, data={"error": "Session is busy processing another request"})
            return

        try:
            async with lock:
                terminal = []
                async with track_run(session, self._run_store):
                    async with contextlib.aclosing(self._run_locked(session, message)) as events:
                        async for event in events:
                            if event.type in {AgentEventType.DONE, AgentEventType.ERROR}:
                                terminal.append(event)
                            else:
                                yield event
                for event in terminal:
                    yield event
        finally:
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
        if session.state_machine.state != TaskState.PROCESSING:
            await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")
        resuming = session._resume_interrupted
        if not resuming:
            session._stop_requested = False
            session._last_iteration = 0
            session.messages.append({"role": MessageRole.USER, "content": message})
            await persist_message(session.session_id, MessageRole.USER, content=message)

        self._set_agent_mode(session)
        self._send_start_notification(session)
        if not resuming:
            await self._inject_memory_context(session, message)
            await self._inject_core_memory(session)

        session._last_result = None
        session._run_status_override = None
        session._last_assistant_message_id = None
        if not resuming:
            await self._save_checkpoint(session, {})
        executor = ParallelToolExecutor(
            self.tool_registry,
            validator=(lambda name, args: validate_tool_call(session, name, args, self.sandbox, self.permission_overlay, self.agent_mode, self.tool_registry)),
            session=session,
        )
        compressor = ContextCompressor(session.context_config)
        result: ChatResult | None = None

        try:
            async with contextlib.aclosing(self._iteration_loop(session, executor, compressor)) as events:
                async for event in events:
                    yield event
        except Exception as e:
            session._last_error = str(e)
            if session._stop_requested:
                await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
            else:
                await session.state_machine.transition(TaskState.FAILED, trigger="unhandled_error")
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

        iteration = session._last_iteration if session._resume_interrupted else 0
        session._resume_interrupted = False
        adapter = self.model_registry.get_or_create(
            provider=session.provider,
            model_id=session.model_id,
            api_key=session.api_key,
            base_url=session.base_url,
        )
        tools = build_tools(self.tool_registry, session.tools, self.tool_prioritizer, task_description=session.messages[-1].get("content", "") if session.messages else "")
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
                        delta = merge_stream_chunk(result, chunk)
                        if session._stop_requested:
                            await self._run_store.record_response(session, result, iteration, complete=False)
                            session.metrics.total_tokens_used += result.tokens_used
                            result = None
                            break
                        if delta:
                            yield AgentEvent(type=AgentEventType.TEXT, data={"content": delta})
                        self._accumulate_stream_tool_calls(result.tool_calls, chunk.tool_calls)
                except BaseException:
                    if result is not None:
                        await self._run_store.record_response(session, result, iteration, complete=False)
                        session.metrics.total_tokens_used += result.tokens_used
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
            result.tokens_used = response_usage(result)["total_tokens"] or 0
            await self._run_store.record_response(session, result, iteration, complete=result.finish_reason != "error")
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
        if not session._stop_requested and iteration >= session.max_iterations and (result is None or result.tool_calls or not result.content):
            await session.state_machine.transition(TaskState.FAILED, trigger="max_iterations")
            session._run_status_override = "max_iterations_reached"
            session._last_error = "Maximum iterations reached"
            await self._save_checkpoint(session, {"final_result": result.content if result else ""})
            return

        if session._stop_requested:
            await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
        else:
            await session.state_machine.transition(TaskState.COMPLETED, trigger="run_complete")
            self._send_completion_notification(session, result)
        await self._save_checkpoint(session, {"final_result": result.content if result else ""})
        yield AgentEvent(type=AgentEventType.CHECKPOINT, data={"iteration": iteration, "final": True})

    async def _save_checkpoint(self, session: AgentSession, channels: dict[str, Any],
                               pending_writes: list[dict[str, Any]] | None = None) -> str:
        from uuid import uuid4
        from app.core.checkpoint import CheckpointData, sanitize_checkpoint

        cp = CheckpointData(
            session_id=session.session_id, messages=session.messages,
            iteration=session._last_iteration, status=session.state_machine.state.value,
            metadata={"thread_id": session.current_turn_id or "", "error": session._last_error},
            channel_values=channels, channel_versions={"messages": session._last_iteration},
            versions_seen={"node": {"messages": session._last_iteration}},
            pending_writes=pending_writes or [],
        )
        cp = sanitize_checkpoint(cp, secrets=(session.api_key,))
        cid = await self._checkpoints.save(None, cp,
            thread_id=session.current_turn_id or "", checkpoint_id=str(uuid4()),
            parent_id=getattr(session, "_last_checkpoint_id", None))
        session._last_checkpoint_id = cid
        return cid

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
        return await adapter.chat(messages=session.messages, tools=tools or None)

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

        When the adapter reports authoritative cumulative content
        (accumulated_content), it is trusted as-is; otherwise per-chunk
        deltas are appended. No prefix-based dedup heuristic is needed.
        """
        result = ChatResult()
        async for chunk in adapter.stream_chat(messages=messages, tools=tools or None):
            merge_stream_chunk(result, chunk)
            if getattr(chunk, "tool_calls", None):
                self._accumulate_stream_tool_calls(result.tool_calls, chunk.tool_calls)
        if result.finish_reason is None:
            result.finish_reason = "tool_calls" if result.tool_calls else "stop"
        return result

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
        await self.resource_tracker.cleanup()

    async def recover_session(self, session: AgentSession) -> bool:
        """Attempt to recover a session from a saved checkpoint.

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

    @staticmethod
    def _accumulate_stream_tool_calls(accumulated: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> None:
        """Merge streamed tool call deltas into complete tool calls."""
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
            tool_call_id = tc.get("id") or f"tool-{iteration}-{len(session.messages)}"
            allowed, reason = self._validate_tool_call(session, function.get("name", ""), arguments)
            event_data = {"id": tool_call_id, "name": function.get("name"), "arguments": arguments}
            if not allowed and isinstance(reason, dict) and reason.get("requires_approval"):
                event_data.update(reason)
                event_data["tool_call_id"] = tool_call_id
                event_data["timeout_seconds"] = self.permission_timeout_seconds
                session._pending_permission = {**event_data, "decision": None}
                session._permission_event = asyncio.Event()
                yield AgentEvent(type=AgentEventType.TOOL_CALL, data=event_data)
                try:
                    await asyncio.wait_for(
                        session._permission_event.wait(),
                        timeout=self.permission_timeout_seconds,
                    )
                except TimeoutError:
                    session._pending_permission["decision"] = "timeout"
                decision = session._pending_permission.get("decision")
                if decision in {"allow", "allow_session", "allow_always"}:
                    approved = getattr(session, "_approved_tool_calls", None)
                    if approved is None:
                        approved = set()
                        session._approved_tool_calls = approved
                    approved.add(_approval_key(function.get("name", ""), arguments))
                session._pending_permission = None
                session._permission_event = None
            else:
                yield AgentEvent(type=AgentEventType.TOOL_CALL, data=event_data)
        await self._save_checkpoint(session, {"last_tool_calls": result.tool_calls},
            pending_writes=[{"channel": "tools", "value": tc,
                             "write_id": tc.get("id", str(index)), "status": "pending"}
                            for index, tc in enumerate(result.tool_calls)])
        tool_results = await executor.execute_all(result.tool_calls)
        session.metrics.total_tool_calls += len(result.tool_calls)
        for tr in tool_results:
            from app.middleware.metrics import TOOL_CALL_LATENCY, TOOL_CALL_TOTAL

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
            session.messages.append({"role": MessageRole.TOOL, "content": tr.result, "tool_call_id": tr.tool_call_id or tr.tool_name})
            await persist_message(
                session.session_id,
                MessageRole.TOOL,
                content=tr.result,
                tool_name=tr.tool_name,
                tool_call_id=tr.tool_call_id,
            )

        await self._save_checkpoint(session, {"last_tool_calls": result.tool_calls,
            "last_tool_results": [tr.result for tr in tool_results], "context_tokens": ctx_tokens})
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
                    tr.result = fixed.output

    def _set_agent_mode(self, session: AgentSession) -> None:
        """Set the current agent mode for tool execution context.

        Args:
            session: The agent session.
        """
        try:
            from app.core.file_patch import set_current_agent_mode
            set_current_agent_mode(session.mode)
        except Exception:
            pass

    def _send_start_notification(self, session: AgentSession) -> None:
        """Send notification when agent starts.

        Args:
            session: The agent session.
        """
        try:
            from app.services.notifications import notification_service
            self._spawn(notification_service.agent_message(session.agent_id or "Agent", "开始执行任务..."))
        except Exception:
            pass

    def _send_completion_notification(self, session: AgentSession, result: Any) -> None:
        """Send notification when agent completes.

        Args:
            session: The agent session.
            result: The final ChatResult.
        """
        try:
            from app.services.notifications import notification_service
            self._spawn(notification_service.task_complete(f"Agent {session.agent_id}", result.content[:100] if result and result.content else None))
        except Exception:
            pass

    def _send_failure_notification(self, session: AgentSession, error: str) -> None:
        """Send notification when agent fails.

        Args:
            session: The agent session.
            error: The error message.
        """
        try:
            from app.services.notifications import notification_service
            self._spawn(notification_service.task_failed(f"Agent {session.agent_id}", error))
        except Exception:
            pass

    def _spawn(self, coro: Any) -> None:
        """Run a fire-and-forget task while holding a reference until it finishes."""
        try:
            task = asyncio.create_task(coro)
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        except Exception:
            pass

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
            pass

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
        except Exception:
            pass

    async def _store_episodic_memory(self, session: AgentSession, message: str) -> None:
        """Store important interaction in episodic memory.

        Args:
            session: The agent session.
            message: The user message.
        """
        try:
            result = getattr(session, "_last_result", None)
            if result and result.content and len(result.content) > 10:
                await self.memory_service.create_episodic_memory(
                    user_id=session.user_id,
                    content=f"User: {message}\nAssistant: {result.content[:500]}",
                    agent_id=session.agent_id,
                    source_session_id=session.session_id,
                    importance=0.7,
                )
        except Exception:
            pass

    def _trigger_memory_reflection(self, session: AgentSession) -> None:
        """Trigger memory reflection (fire-and-forget).

        Args:
            session: The agent session.
        """
        try:
            from app.core.memory_reflection import memory_reflection
            self._spawn(memory_reflection.maybe_reflect(session.user_id))
        except Exception:
            pass

    def resolve_permission(self, tool_call_id: str, decision: str) -> bool:
        """Resolve a pending permission request.

        Args:
            tool_call_id: The ID of the tool call awaiting permission.
            decision: One of 'allow', 'allow_session', 'allow_always', 'deny'.

        Returns:
            True if the permission was resolved, False if no pending request found.
        """
        for session in self._sessions.values():
            if session._pending_permission and session._pending_permission.get("tool_call_id") == tool_call_id:
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
