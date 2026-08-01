from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, AsyncIterator

import structlog

from app.core import AgentEvent, AgentEventType, ContextConfig, MessageRole
from app.core.checkpoint import InMemoryCheckpointStore
from app.core.di import resolve as di_resolve
from app.core.engine.react_loop import ReActLoopExecutor
from app.core.engine.safety import setup_default_permissions, validate_tool_call
from app.core.engine.session import AgentSession
from app.core.engine.tool_builder import build_tools as _build_tools_impl
from app.core.frame import Frame, FrameFolder, FrameKind, FrameType
from app.core.persistent_memory import PersistentMemoryService
from app.core.permission_rules import PermissionConfig, RuleDecision, get_default_config
from app.core.task_state_machine import TaskState
from app.core.tool_prioritizer import ToolPrioritizer

if TYPE_CHECKING:
    from app.models.registry import ModelRegistry
    from app.tools import ToolRegistry

logger = structlog.get_logger()


class AgentEngine:
    def __init__(self, model_registry: ModelRegistry | None = None, tool_registry: ToolRegistry | None = None, checkpoint_store: InMemoryCheckpointStore | None = None):
        self.model_registry = model_registry or di_resolve("ModelRegistry")
        self.tool_registry = tool_registry or di_resolve("ToolRegistry")
        self._checkpoints = checkpoint_store or InMemoryCheckpointStore()
        self._sessions: dict[str, AgentSession] = {}
        self.memory_service = PersistentMemoryService()
        self.tool_prioritizer = ToolPrioritizer()
        self._seq_counter: int = 0
        self._permission_config = get_default_config()
        self._permission_events: dict[str, asyncio.Event] = {}
        self._permission_resolutions: dict[str, str] = {}
        self._denied_tool_calls: set[str] = set()
        self._frame_folder = FrameFolder()
        try:
            from app.core.debug_loop import DebugLoopEngine
            self.debug_loop = DebugLoopEngine(model_registry=self.model_registry)
        except Exception:
            self.debug_loop = None
        try:
            from app.core.security_sandbox import SecuritySandbox, SandboxConfig, PermissionOverlay, AgentMode
            import os
            workdir = os.environ.get("CLIMBER_SANDBOX_WORKDIR") or os.getcwd()
            self.sandbox = SecuritySandbox(SandboxConfig(workdir=workdir))
            self.permission_overlay = PermissionOverlay()
            setup_default_permissions(self.permission_overlay)
            self.agent_mode = AgentMode.ACT
        except Exception:
            self.sandbox = None
            self.permission_overlay = None
            self.agent_mode = None

        self._loop_executor = ReActLoopExecutor(
            model_registry=self.model_registry,
            tool_registry=self.tool_registry,
            checkpoint_store=self._checkpoints,
            tool_prioritizer=self.tool_prioritizer,
            build_tools_fn=self._build_tools,
            validate_tool_call_fn=self._validate_tool_call if self.sandbox else None,
        )

    def _validate_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        return validate_tool_call(
            self.sandbox, self.permission_overlay, self.agent_mode,
            self.tool_registry, tool_name, arguments,
        )

    def _build_tools(self, tool_names: list[str], task_description: str = "") -> list[dict[str, Any]]:
        return _build_tools_impl(self.tool_registry, self.tool_prioritizer, tool_names, task_description)

    def _next_seq(self) -> int:
        self._seq_counter += 1
        return self._seq_counter

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
        # 注入 MemFS 记忆到系统提示词 (参考 Letta system/ 目录)
        memfs_context = self._load_memfs_context_sync(user_id, agent_id)
        if memfs_context:
            session.messages.append({"role": MessageRole.SYSTEM, "content": memfs_context})
        # 注入角色化 Agent 的 system prompt (参考 CrewAI role+goal+backstory)
        if not system_prompt:
            role_prompt = self._load_role_prompt_sync(agent_id)
            if role_prompt:
                system_prompt = role_prompt
        # 注入内置提示词模板 (参考 prompt_engine/template_repository.py)
        if not system_prompt:
            builtin = self._get_builtin_prompt(agent_id)
            if builtin:
                system_prompt = builtin
        if system_prompt:
            session.messages.append({"role": MessageRole.SYSTEM, "content": system_prompt})
        self._sessions[session_id] = session
        return session

    def _load_memfs_context_sync(self, user_id: str, agent_id: str) -> str:
        """同步加载 MemFS persona 和 human 偏好记忆"""
        try:
            import asyncio
            from app.core.memfs import MemFS
            memfs = MemFS(base_path=f"data/memfs/{user_id}/{agent_id}")
            # 尝试获取现有 loop，否则创建新 loop
            try:
                loop = asyncio.get_running_loop()
                # 已在 loop 中，创建 task（但这里不能 await，返回空）
                return ""
            except RuntimeError:
                # 无运行中的 loop，可以安全使用 run
                async def _read():
                    persona = await memfs.read("system/persona.md")
                    human = await memfs.read("system/human.md")
                    parts = []
                    if persona:
                        parts.append(f"# Your Identity\n{persona}")
                    if human:
                        parts.append(f"# About Your Human\n{human}")
                    return "\n\n".join(parts) if parts else ""
                return asyncio.run(_read())
        except Exception:
            return ""

    def _load_role_prompt_sync(self, agent_id: str) -> str:
        """同步加载角色化 Agent 定义的 system prompt"""
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                return ""  # 在 loop 中无法 sync 等待
            except RuntimeError:
                from app.core.role_agent import AgentProfile
                from app.storage import async_session
                from app.storage.database import Agent as AgentModel
                from sqlalchemy import select
                async def _query():
                    async with async_session() as db:
                        result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
                        row = result.scalar_one_or_none()
                        if row and row.agent_role:
                            profile = AgentProfile(
                                id=agent_id,
                                role=row.agent_role or "",
                                goal=row.goal or "",
                                backstory=row.backstory or "",
                                tools=list(row.tool_ids or []),
                            )
                            return profile.system_prompt()
                    return ""
                return asyncio.run(_query())
        except Exception:
            return ""

    async def _load_memfs_context(self, user_id: str, agent_id: str) -> str:
        """从 MemFS 加载 agent persona 和 human 偏好记忆"""
        try:
            from app.core.memfs import MemFS
            memfs = MemFS(base_path=f"data/memfs/{user_id}/{agent_id}")
            persona = memfs.read("system/persona.md")
            human = memfs.read("system/human.md")
            parts = []
            if persona:
                parts.append(f"# Your Identity\n{persona}")
            if human:
                parts.append(f"# About Your Human\n{human}")
            return "\n\n".join(parts) if parts else ""
        except Exception:
            return ""

    async def _load_role_prompt(self, user_id: str, agent_id: str) -> str:
        """加载角色化 Agent 定义的 system prompt"""
        try:
            from app.core.role_agent import AgentProfile
            from app.storage import async_session
            from app.storage.database import Agent as AgentModel
            from sqlalchemy import select
            async with async_session() as db:
                result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
                row = result.scalar_one_or_none()
                if row and row.agent_role:
                    profile = AgentProfile(
                        id=agent_id,
                        role=row.agent_role or "",
                        goal=row.goal or "",
                        backstory=row.backstory or "",
                        tools=list(row.tool_ids or []),
                    )
                    return profile.system_prompt()
        except Exception:
            pass
        return ""

    def _get_builtin_prompt(self, agent_id: str) -> str:
        """获取内置提示词模板"""
        try:
            from app.core.prompt_engine.template_repository import PromptTemplateRepository
            repo = PromptTemplateRepository()
            templates = repo.list_builtins()
            if templates:
                return templates[0].content
        except Exception:
            pass
        return ""

    async def run(self, session: AgentSession, message: str) -> AsyncIterator[AgentEvent]:
        await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")
        session.messages.append({"role": MessageRole.USER, "content": message})

        try:
            from app.core.file_patch import set_current_agent_mode
            set_current_agent_mode(session.mode)
        except Exception as e:
            logger.warning("agent_engine.set_agent_mode_failed", error=str(e))

        try:
            from app.services.notifications import notification_service
            asyncio.create_task(notification_service.agent_message(session.agent_id or "Agent", "Agent started task"))
        except Exception as e:
            logger.warning("agent_engine.notification_start_failed", error=str(e))

        try:
            memory_context = await self.memory_service.format_memories_for_prompt(
                user_id=session.user_id,
                query=message,
                max_memories=5,
            )
            if memory_context:
                session.messages.insert(-1, {"role": MessageRole.SYSTEM, "content": memory_context})
        except Exception as e:
            logger.warning("agent_engine.memory_injection_failed", error=str(e))

        try:
            from app.core.core_memory import core_memory
            blocks = await core_memory.get_blocks(user_id=session.user_id, agent_id=session.agent_id)
            if blocks:
                core_memory_xml = core_memory.format_for_prompt(blocks)
                session.messages.insert(-1, {"role": MessageRole.SYSTEM, "content": core_memory_xml})
        except Exception as e:
            logger.warning("agent_engine.core_memory_injection_failed", error=str(e))

        result_content = ""
        iterations = 0

        yield self._frame_to_event(Frame(
            type=FrameType.SESSION_START,
            kind=FrameKind.INFO,
            data={"sessionId": session.session_id, "message": message},
            seq=self._next_seq(),
        ))

        try:
            async for event in self._loop_executor.execute(session, message, on_error=_notify_error):
                async for frame in self._event_to_frames(event, session):
                    if frame is not None:
                        yield self._frame_to_event(frame)

                if event.type == AgentEventType.DONE:
                    result_content = event.data.get("content", "")
                    iterations = event.data.get("iterations", 0)
        except Exception as e:
            logger.error("agent_engine.loop_executor_failed", error=str(e))
            yield self._frame_to_event(Frame(
                type=FrameType.ERROR,
                kind=FrameKind.ERROR,
                data={"error": str(e)},
                seq=self._next_seq(),
            ))
            await session.state_machine.transition(TaskState.FAILED, trigger="loop_executor_error")
            return

        try:
            if result_content and len(result_content) > 10:
                await self.memory_service.create_episodic_memory(
                    user_id=session.user_id,
                    content=f"User: {message}\nAssistant: {result_content[:500]}",
                    agent_id=session.agent_id,
                    source_session_id=session.session_id,
                    importance=0.7,
                )
        except Exception as e:
            logger.warning("agent_engine.episodic_memory_failed", error=str(e))

        try:
            from app.core.memory_reflection import memory_reflection
            asyncio.create_task(memory_reflection.maybe_reflect(session.user_id))
        except Exception as e:
            logger.warning("agent_engine.memory_reflection_failed", error=str(e))

        try:
            from app.services.notifications import notification_service
            asyncio.create_task(notification_service.task_complete(f"Agent {session.agent_id}", result_content[:100] if result_content else None))
        except Exception as e:
            logger.warning("agent_engine.notification_complete_failed", error=str(e))

        # 触发后台记忆整合 (参考 Letta Dreaming)
        asyncio.create_task(self._trigger_dreaming(session.session_id, session.user_id, session.agent_id))

        yield self._frame_to_event(Frame(
            type=FrameType.SESSION_END,
            kind=FrameKind.SUCCESS,
            data={"content": result_content, "iterations": iterations, "status": "completed"},
            seq=self._next_seq(),
        ))

    async def _trigger_dreaming(self, session_id: str, user_id: str, agent_id: str) -> None:
        """触发后台记忆整合"""
        try:
            from app.core.dreaming_engine import DreamingEngine, ConsolidationConfig
            from app.core.memfs import MemFS
            memfs = MemFS(base_path=f"data/memfs/{user_id}/{agent_id}")
            config = ConsolidationConfig(message_threshold=3)
            engine = DreamingEngine(memfs=memfs, config=config)
            await engine.consolidate(session_id)
        except Exception as e:
            logger.debug("agent_engine.dreaming_skipped", error=str(e))

    @staticmethod
    def _frame_to_event(frame: Frame) -> AgentEvent:
        """将 Frame 映射为 AgentEvent — 保持向后兼容

        Frame 类型映射到 AgentEventType，
        并将 Frame.data 展平到 AgentEvent.data 中，
        使旧代码 event.data["content"] 仍可用。
        """
        type_map = {
            FrameType.MESSAGE_TOKEN: AgentEventType.TEXT,
            FrameType.THINKING_TOKEN: AgentEventType.THINKING,
            FrameType.TOOL_CALL: AgentEventType.TOOL_CALL,
            FrameType.TOOL_RESULT: AgentEventType.TOOL_RESULT,
            FrameType.PERMISSION_REQ: AgentEventType.TOOL_CALL,
            FrameType.PERMISSION_RESOLVED: AgentEventType.TOOL_RESULT,
            FrameType.ERROR: AgentEventType.ERROR,
            FrameType.SESSION_START: AgentEventType.TEXT,
            FrameType.SESSION_END: AgentEventType.DONE,
            FrameType.PLAN_UPDATE: AgentEventType.PROGRESS,
        }
        event_type = type_map.get(frame.type, AgentEventType.TEXT)
        # 展平 Frame.data 并附加 Frame 元数据
        flat_data = dict(frame.data)
        flat_data["_frame"] = frame.to_dict()
        return AgentEvent(
            type=event_type,
            data=flat_data,
        )

    async def _event_to_frames(self, event: AgentEvent, session: AgentSession) -> AsyncIterator[Frame | None]:
        if event.type == AgentEventType.TEXT:
            frame = Frame.message_token(content=event.data.get("content", ""), seq=self._next_seq())
            folded = self._frame_folder.add(frame)
            if folded is not None:
                yield folded
        elif event.type == AgentEventType.THINKING:
            frame = Frame.thinking_token(content="", seq=self._next_seq())
            yield frame
        elif event.type == AgentEventType.TOOL_CALL:
            tool_name = event.data.get("name", "")
            tool_id = event.data.get("id", "")
            arguments = event.data.get("arguments", {})

            decision = self._permission_config.evaluate(tool_name, arguments)

            if decision == RuleDecision.DENY:
                self._denied_tool_calls.add(tool_name)
                yield Frame.permission_req(
                    tool_call_id=tool_id,
                    action=self._map_tool_to_action(tool_name),
                    description=f"Permission denied for tool: {tool_name}",
                    severity="high",
                    seq=self._next_seq(),
                )
                yield Frame.permission_resolved(
                    tool_call_id=tool_id,
                    decision="deny",
                    seq=self._next_seq(),
                )
                yield Frame.tool_call(
                    name=tool_name,
                    arguments=arguments if isinstance(arguments, dict) else {},
                    seq=self._next_seq(),
                )
                yield Frame.tool_result(
                    name=tool_name,
                    error="Permission denied by rule",
                    seq=self._next_seq(),
                )
                return

            if decision == RuleDecision.ASK:
                req_event = asyncio.Event()
                self._permission_events[tool_id] = req_event

                yield Frame.permission_req(
                    tool_call_id=tool_id,
                    action=self._map_tool_to_action(tool_name),
                    description=f"Allow tool call: {tool_name}?",
                    details=self._format_tool_details(tool_name, arguments),
                    severity=self._permission_config.assess_risk(tool_name, arguments),
                    seq=self._next_seq(),
                )

                await req_event.wait()

                decision_result = self._permission_resolutions.pop(tool_id, "deny")
                self._permission_events.pop(tool_id, None)

                yield Frame.permission_resolved(
                    tool_call_id=tool_id,
                    decision=decision_result,
                    seq=self._next_seq(),
                )

                if decision_result == "deny":
                    self._denied_tool_calls.add(tool_name)
                    yield Frame.tool_call(
                        name=tool_name,
                        arguments=arguments if isinstance(arguments, dict) else {},
                        seq=self._next_seq(),
                    )
                    yield Frame.tool_result(
                        name=tool_name,
                        error="Permission denied by user",
                        seq=self._next_seq(),
                    )
                    return

            yield Frame.tool_call(
                name=tool_name,
                arguments=arguments if isinstance(arguments, dict) else {},
                seq=self._next_seq(),
            )

        elif event.type == AgentEventType.TOOL_RESULT:
            tool_name = event.data.get("tool_name", "")
            if tool_name in self._denied_tool_calls:
                self._denied_tool_calls.discard(tool_name)
                return
            yield Frame.tool_result(
                name=tool_name,
                result=event.data.get("result"),
                error=event.data.get("error"),
                seq=self._next_seq(),
            )
        elif event.type == AgentEventType.DONE:
            yield Frame(
                type=FrameType.MESSAGE_END,
                kind=FrameKind.SUCCESS,
                data={"content": event.data.get("content", ""), "iterations": event.data.get("iterations", 0)},
                seq=self._next_seq(),
            )
        elif event.type == AgentEventType.ERROR:
            yield Frame(
                type=FrameType.ERROR,
                kind=FrameKind.ERROR,
                data={"error": event.data.get("error", "")},
                seq=self._next_seq(),
            )
        elif event.type == AgentEventType.CONTEXT_COMPRESSION:
            yield Frame(
                type=FrameType.STATUS,
                kind=FrameKind.WARN,
                data={"status": "compressing", "iteration": event.data.get("iteration", 0)},
                seq=self._next_seq(),
            )
        else:
            yield Frame(
                type=FrameType.STATUS,
                kind=FrameKind.INFO,
                data={"event": event.type.value, **event.data},
                seq=self._next_seq(),
            )

    def _map_tool_to_action(self, tool_name: str) -> str:
        if tool_name in ("bash", "run_command", "native_run", "command"):
            return "command"
        if tool_name in ("read_file", "file_read"):
            return "file_read"
        if tool_name in ("write_file", "file_write", "edit"):
            return "file_write"
        if tool_name in ("file_delete", "delete", "rm"):
            return "file_delete"
        if tool_name in ("web_search", "http_request", "fetch", "native_web_search"):
            return "network"
        return "mcp_tool"

    def _format_tool_details(self, tool_name: str, arguments: Any) -> str | None:
        if isinstance(arguments, dict):
            import json
            return json.dumps(arguments, ensure_ascii=False, indent=2)
        return str(arguments) if arguments else None

    def resolve_permission(self, tool_call_id: str, decision: str) -> bool:
        if tool_call_id in self._permission_events:
            self._permission_resolutions[tool_call_id] = decision
            self._permission_events[tool_call_id].set()
            return True
        return False

    def get_permission_config(self) -> PermissionConfig:
        return self._permission_config

    def update_permission_config(self, config: PermissionConfig) -> None:
        self._permission_config = config


def _notify_error(error: str) -> None:
    try:
        from app.services.notifications import notification_service
        asyncio.create_task(notification_service.task_failed("Agent", error))
    except Exception as e:
        logger.warning("agent_engine.notification_failed_failed", error=str(e))
