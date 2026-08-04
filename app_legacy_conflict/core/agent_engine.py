"""Minimal agent engine with ReAct loop."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from typing import Any

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
from app.core.parallel import ParallelToolExecutor
from app.core.persistent_memory import PersistentMemoryService
from app.core.task_state_machine import TaskState, TaskStateMachine
from app.core.tool_prioritizer import ToolPrioritizer
from app.models.openai_adapter import OpenAIAdapter


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
        # State machine: use TaskState for unified lifecycle management
        self.state_machine = TaskStateMachine(task_id=session_id, initial_state=TaskState.PENDING)
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
        self._pending_permission: dict[str, Any] | None = None
        self._permission_event: asyncio.Event | None = None
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
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.state_machine.transition(TaskState.CANCELLED, trigger="user_stop"))
        except RuntimeError:
            pass

    async def pause(self) -> None:
        """Pause the session, recording the pause timestamp."""
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
    def __init__(self, model_registry: ModelRegistry | None = None, tool_registry: ToolRegistry | None = None, checkpoint_store: InMemoryCheckpointStore | None = None):
        self.model_registry = model_registry or di_resolve("ModelRegistry")
        self.tool_registry = tool_registry or di_resolve("ToolRegistry")
        self._checkpoints = checkpoint_store or InMemoryCheckpointStore()
        self._sessions: dict[str, AgentSession] = {}
        self._session_locks: dict[str, asyncio.Lock] = {}
        self.memory_service = PersistentMemoryService()
        # Tool prioritization with lightweight learning (reference: Suna)
        self.tool_prioritizer = ToolPrioritizer()
        # Auto-debug loop (reference: Devika failure debugging closed loop)
        try:
            from app.core.debug_loop import DebugLoopEngine
            self.debug_loop = DebugLoopEngine(model_registry=self.model_registry)
        except Exception:
            self.debug_loop = None
        # Security sandbox: rejects hazard commands and out-of-scope file access before execution
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

    # Tool names that accept a shell command under a "command" parameter
    _COMMAND_TOOLS = {"run_command", "shell", "execute_command", "bash"}
    # Tool names that perform file IO under path/file parameters
    _FILE_TOOLS = {
        "read_file": ("path", "read"),
        "write_file": ("path", "write"),
        "edit_file": ("path", "write"),
        "append_file": ("path", "write"),
        "file_exists": ("path", "read"),
        "file_info": ("path", "read"),
        "file_diff": ("path", "read"),
        "list_directory": ("dir", "read"),
    }

    def _validate_tool_call(self, session: AgentSession, tool_name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        """Pre-execution safety check. Returns (allowed, reason)."""
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
                return False, f"Permission required: {tool_name}"

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
                return False, f"Permission required: {action} on {resource}"

        # JSON Schema validation
        try:
            from app.core.security_sandbox import validate_tool_input
            tool_def = self.tool_registry.get_tool(tool_name)
            if tool_def and tool_def.parameters:
                validate_tool_input(tool_def.parameters, arguments)
        except Exception as e:
            return False, str(e)

        # Existing sandbox checks
        if self.sandbox is None:
            return True, "OK"
        try:
            if tool_name in self._COMMAND_TOOLS:
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
        return True, "OK"

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

    async def _persist_message(
        self,
        session_id: str,
        role: str,
        content: str | None = None,
        tool_calls: list[dict] | None = None,
        tool_name: str | None = None,
        tokens: int = 0,
    ) -> None:
        """Persist a message to the database (fire-and-forget)."""
        try:
            from app.storage import async_session
            from app.storage.database import Message

            async with async_session() as db:
                msg = Message(
                    session_id=session_id,
                    role=role,
                    content=content,
                    tool_calls=tool_calls or [],
                    tool_name=tool_name,
                    tokens=tokens,
                )
                db.add(msg)
                await db.commit()
        except Exception:
            pass

    async def run(self, session: AgentSession, message: str) -> AsyncIterator[AgentEvent]:
        # Acquire session-level lock to prevent concurrent requests
        if session.session_id not in self._session_locks:
            self._session_locks[session.session_id] = asyncio.Lock()

        lock = self._session_locks[session.session_id]
        if lock.locked():
            yield AgentEvent(type=AgentEventType.ERROR, data={"error": "Session is busy processing another request"})
            return

        try:
            async with lock:
                async for event in self._run_locked(session, message):
                    yield event
        finally:
            self._session_locks.pop(session.session_id, None)

    async def _run_locked(self, session: AgentSession, message: str) -> AsyncIterator[AgentEvent]:
        """Internal run method — executes under session lock."""
        # Allow restart: COMPLETED/FAILED/CANCELLED sessions must reset to PENDING first
        current = session.state_machine.state
        if current in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
            await session.state_machine.transition(TaskState.PENDING, trigger="user_restart")
        # Transition to PROCESSING state via state machine
        await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")
        session.messages.append({"role": MessageRole.USER, "content": message})
        await self._persist_message(session.session_id, MessageRole.USER, content=message)

        # Set current agent mode for tool execution context (e.g., PLAN vs ACT)
        try:
            from app.core.file_patch import set_current_agent_mode
            set_current_agent_mode(session.mode)
        except Exception:
            pass

        # Fire-and-forget notification for agent start
        try:
            from app.services.notifications import notification_service
            asyncio.create_task(notification_service.agent_message(session.agent_id or "Agent", "开始执行任务..."))
        except Exception:
            pass

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
            pass

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
            pass

        iteration = 0
        executor = ParallelToolExecutor(
            self.tool_registry,
            validator=(lambda name, args: self._validate_tool_call(session, name, args)) if self.sandbox else None,
            session=session,
        )
        compressor = ContextCompressor(session.context_config)
        result: ChatResult | None = None

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

                ctx_tokens = estimate_tokens(session.messages)
                ctx_limit = getattr(adapter.capabilities, "max_tokens", None) or session.context_config.max_tokens
                if compressor.needs_compression(session.messages) or (ctx_limit and ctx_tokens > ctx_limit * 0.8):
                    session.messages = await compressor.compress(session.messages, adapter)
                    yield AgentEvent(type=AgentEventType.CONTEXT_COMPRESSION, data={"iteration": iteration, "tokens": ctx_tokens, "limit": ctx_limit})

                try:
                    if adapter.capabilities.streaming:
                        full_content = ""
                        accumulated_tool_calls = []
                        total_tokens = 0
                        async for chunk in adapter.stream_chat(messages=session.messages, tools=tools or None):
                            if session._stop_requested:
                                yield AgentEvent(type=AgentEventType.STOPPED, data={"reason": "user_requested"})
                                await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
                                return
                            if chunk.content:
                                full_content += chunk.content
                                yield AgentEvent(type=AgentEventType.TEXT, data={"content": chunk.content})
                            for tc in chunk.tool_calls:
                                idx = tc.get("index", 0) if "index" in tc else 0
                                while len(accumulated_tool_calls) <= idx:
                                    accumulated_tool_calls.append({
                                        "id": "",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""},
                                    })
                                if tc.get("id"):
                                    accumulated_tool_calls[idx]["id"] = tc["id"]
                                if tc.get("function", {}).get("name"):
                                    accumulated_tool_calls[idx]["function"]["name"] = tc["function"]["name"]
                                if tc.get("function", {}).get("arguments"):
                                    new_args = tc["function"]["arguments"]
                                    if isinstance(new_args, dict):
                                        new_args = json.dumps(new_args, ensure_ascii=False)
                                    elif not isinstance(new_args, str):
                                        new_args = str(new_args)
                                    accumulated_tool_calls[idx]["function"]["arguments"] += new_args
                            if hasattr(chunk, 'usage') and chunk.usage:
                                total_tokens = chunk.usage
                            elif hasattr(chunk, 'tokens_used') and chunk.tokens_used:
                                total_tokens = chunk.tokens_used
                        result = ChatResult(content=full_content, tool_calls=accumulated_tool_calls, finish_reason="stop", tokens_used=total_tokens)
                    else:
                        result = await adapter.chat(messages=session.messages, tools=tools or None)
                except Exception as e:
                    if session._stop_requested:
                        yield AgentEvent(type=AgentEventType.ERROR, data={"error": str(e)})
                        await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
                        return
                    yield AgentEvent(type=AgentEventType.ERROR, data={"error": str(e)})
                    await session.state_machine.transition(TaskState.FAILED, trigger="llm_error")
                    return

                # Parse XML-style tool calls for non-standard providers (e.g., StepFun)
                if not result.tool_calls and result.content:
                    xml_tool_calls = OpenAIAdapter._parse_xml_tool_calls(result.content)
                    if xml_tool_calls:
                        result.tool_calls = xml_tool_calls
                        cleaned = re.sub(r'<function([^>]+)>.*?</\1>', '', result.content, flags=re.DOTALL | re.IGNORECASE).strip()
                        if not cleaned:
                            result.content = ""

                if result.content:
                    session.messages.append({"role": MessageRole.ASSISTANT, "content": result.content})
                    await self._persist_message(
                        session.session_id,
                        MessageRole.ASSISTANT,
                        content=result.content,
                        tokens=getattr(result, 'tokens_used', 0),
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
                    )
                    for tc in result.tool_calls:
                        yield AgentEvent(type=AgentEventType.TOOL_CALL, data={"id": tc.get("id"), "name": tc.get("function", {}).get("name"), "arguments": tc.get("function", {}).get("arguments", {})})
                    tool_results = await executor.execute_all(result.tool_calls)
                    for tr in tool_results:
                        self.tool_prioritizer.record_outcome(
                            tr.tool_name,
                            tr.success,
                            tr.duration_ms,
                        )
                        yield AgentEvent(type=AgentEventType.TOOL_RESULT, data={"tool_name": tr.tool_name, "result": tr.result, "error": tr.error})

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

                        session.messages.append({"role": MessageRole.TOOL, "content": tr.result, "tool_call_id": tr.tool_call_id or tr.tool_name})
                        await self._persist_message(
                            session.session_id,
                            MessageRole.TOOL,
                            content=tr.result,
                            tool_name=tr.tool_name,
                        )

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
                    await self._checkpoints.save(None, cp, checkpoint_id=f"{session.session_id}-{iteration}")
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
                await self._checkpoints.save(None, cp, checkpoint_id=f"{session.session_id}-{iteration}")
                yield AgentEvent(type=AgentEventType.CHECKPOINT, data={"iteration": iteration})
                break

            if iteration >= session.max_iterations and result and result.tool_calls:
                await session.state_machine.transition(TaskState.FAILED, trigger="max_iterations")
                yield AgentEvent(type=AgentEventType.DONE, data={"status": "max_iterations_reached", "iterations": iteration})
                return

            if session._stop_requested:
                await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
            else:
                await session.state_machine.transition(TaskState.COMPLETED, trigger="run_complete")
                try:
                    from app.services.notifications import notification_service
                    asyncio.create_task(notification_service.task_complete(f"Agent {session.agent_id}", result.content[:100] if result and result.content else None))
                except Exception:
                    pass

        except Exception as e:
            if session._stop_requested:
                await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
            else:
                await session.state_machine.transition(TaskState.FAILED, trigger="unhandled_error")
            yield AgentEvent(type=AgentEventType.ERROR, data={"error": str(e)})
            try:
                from app.services.notifications import notification_service
                asyncio.create_task(notification_service.task_failed(f"Agent {session.agent_id}", str(e)))
            except Exception:
                pass
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
            pass

        # Trigger memory reflection (fire-and-forget)
        try:
            from app.core.memory_reflection import memory_reflection
            asyncio.create_task(memory_reflection.maybe_reflect(session.user_id))
        except Exception:
            pass

        yield AgentEvent(type=AgentEventType.DONE, data={"status": session.status.value, "iterations": iteration, "content": result.content if result else "", "tokens_used": getattr(result, 'tokens_used', 0) if result else 0})



    def _build_tools(self, tool_names: list[str], task_description: str = "") -> list[dict[str, Any]]:
        if task_description and len(tool_names) > 1:
            available: list[dict[str, Any]] = []
            for name in tool_names:
                defn = self.tool_registry.get_tool(name)
                if defn:
                    available.append({
                        "type": "function",
                        "function": {
                            "name": defn.name,
                            "description": defn.description,
                            "parameters": defn.parameters,
                        },
                    })
            ranked = self.tool_prioritizer.rank_tools(task_description, available)
            name_to_defn = {name: self.tool_registry.get_tool(name) for name in tool_names}
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
        """Get the default permission configuration."""
        try:
            from app.core.permission_rules import get_default_config
            return get_default_config()
        except Exception:
            from app.core.permission_rules import PermissionConfig
            return PermissionConfig()

    def update_permission_config(self, config: Any) -> None:
        """Update the default permission configuration for new sessions."""
        self._default_permission_config = config
