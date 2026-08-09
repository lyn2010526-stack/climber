from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.core import ContextConfig, SessionStatus
from app.core.task_state_machine import TaskState, TaskStateMachine


class _SessionMemory:
    def __init__(self, session: AgentSession) -> None:
        self._session = session

    def add(self, role: str, content: str) -> None:
        self._session.messages.append({"role": role, "content": content})


class AgentSession:
    def __init__(
        self,
        session_id: str,
        agent_id: str,
        user_id: str,
        provider: str,
        model_id: str,
        api_key: str,
        base_url: str | None = None,
        system_prompt: str = "",
        tools: list[str] | None = None,
        context_config: ContextConfig | None = None,
        mode: str = "act",
    ):
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
        self.state_machine = TaskStateMachine(task_id=session_id, initial_state=TaskState.PENDING)
        self.mode = mode
        self.debug_attempts: dict[str, int] = {}
        self.current_turn_id: str | None = None
        self.restart_count: int = 0
        self.paused_at: datetime | None = None
        self.termination_reason: str | None = None
        self._pending_tasks: set[asyncio.Task] = set()

    @property
    def status(self) -> SessionStatus:
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
            loop = asyncio.get_running_loop()
            loop.create_task(self.state_machine.transition(TaskState.CANCELLED, trigger="user_stop"))
        except RuntimeError:
            pass

    async def pause(self) -> None:
        await self.state_machine.transition(TaskState.PAUSED, trigger="user_pause")
        self.paused_at = datetime.now(timezone.utc)

    async def resume(self) -> None:
        await self.state_machine.transition(TaskState.PROCESSING, trigger="user_resume")
        self.paused_at = None

    async def terminate(self, reason: str = "user_terminated") -> None:
        self.termination_reason = reason
        await self.state_machine.transition(TaskState.CANCELLED, trigger="user_abort")

    async def restart(self) -> None:
        self.restart_count += 1
        self._stop_requested = False
        self.termination_reason = None
        self.paused_at = None
        await self.state_machine.transition(TaskState.PENDING, trigger="user_restart")

    def _fire_and_forget(self, coro: Any) -> None:
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    async def _await_pending_tasks(self) -> None:
        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)
            self._pending_tasks.clear()