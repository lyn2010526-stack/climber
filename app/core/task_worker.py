"""Task worker — persistent async task execution with progress tracking."""
from __future__ import annotations

import asyncio
import json
import uuid
from collections import OrderedDict, defaultdict, deque
from collections.abc import Callable, Coroutine
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import structlog

from app.storage import async_session
from app.storage.models_platform import AutoLoopTask

logger = structlog.get_logger()

_SENSITIVE_PAYLOAD_KEYS = {"api_key", "api_key_encrypted"}


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    task_id: str
    task_type: str
    status: TaskStatus
    payload: dict[str, Any]
    result: Any = None
    error: str | None = None
    progress: int = 0
    total_steps: int = 0
    current_step: int = 0
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class TaskManager:
    """Manages task lifecycle: submit, execute, track, cancel."""

    def __init__(self, max_workers: int = 3):
        self._handlers: dict[str, Callable[..., Coroutine]] = {}
        self._semaphore = asyncio.Semaphore(max_workers)
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._progress_callbacks: list[Callable[[str, dict], Coroutine]] = []
        self._event_history: OrderedDict[str, deque[dict[str, Any]]] = OrderedDict()
        self._event_subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)

    def register(self, task_type: str, handler: Callable[..., Coroutine]) -> None:
        self._handlers[task_type] = handler

    def on_progress(self, callback: Callable[[str, dict], Coroutine]) -> None:
        self._progress_callbacks.append(callback)

    def subscribe(self, task_id: str) -> asyncio.Queue[dict[str, Any]]:
        """Subscribe to task-specific lifecycle events, replaying recent history."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        for event in self._event_history.get(task_id, ()):
            queue.put_nowait(event)
        self._event_subscribers[task_id].add(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        subscribers = self._event_subscribers.get(task_id)
        if subscribers is None:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._event_subscribers.pop(task_id, None)
            while len(self._event_history) > 100:
                self._event_history.popitem(last=False)

    async def emit_event(self, task_id: str, event_type: str, data: dict[str, Any]) -> None:
        event = {"type": event_type, "data": data}
        history = self._event_history.setdefault(task_id, deque(maxlen=100))
        history.append(event)
        self._event_history.move_to_end(task_id)
        while len(self._event_history) > 100:
            removable = next(
                (
                    history_task_id
                    for history_task_id in self._event_history
                    if not self._event_subscribers.get(history_task_id)
                ),
                None,
            )
            if removable is None:
                break
            self._event_history.pop(removable, None)
        for queue in tuple(self._event_subscribers.get(task_id, ())):
            queue.put_nowait(event)

    async def submit(self, task_type: str, payload: dict[str, Any]) -> str:
        if task_type not in self._handlers:
            raise ValueError(f"Unknown task type: {task_type}")

        task_id = str(uuid.uuid4())[:12]
        now = datetime.now(UTC)

        async with async_session() as session:
            persisted_payload = {
                key: value
                for key, value in payload.items()
                if key not in _SENSITIVE_PAYLOAD_KEYS
            }
            record = AutoLoopTask(
                id=task_id,
                objective=json.dumps({"type": task_type, **persisted_payload}),
                status=TaskStatus.PENDING.value,
                max_steps=payload.get("max_steps", 10),
                current_step=0,
                result=None,
                error=None,
                created_at=now,
                updated_at=now,
                started_at=None,
                finished_at=None,
                heartbeat_at=now,
            )
            session.add(record)
            await session.commit()

        worker = asyncio.create_task(self._run_task(task_id, task_type, payload))
        self._active_tasks[task_id] = worker
        worker.add_done_callback(lambda _task: self._active_tasks.pop(task_id, None))
        return task_id

    async def cancel(self, task_id: str) -> bool:
        task = self._active_tasks.get(task_id)
        if task is None or task.done() or task.cancelling():
            return False
        task.cancel()
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if record:
                record.status = TaskStatus.CANCELLED.value
                record.finished_at = datetime.now(UTC)
                await session.commit()
        return True

    async def get_status(self, task_id: str) -> dict[str, Any] | None:
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            if not record:
                return None
            return {
                "task_id": record.id,
                "objective": self._objective_from_record(record.objective),
                "status": record.status,
                "progress": record.current_step,
                "total_steps": record.max_steps,
                "result": record.result,
                "error": record.error,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "started_at": record.started_at.isoformat() if record.started_at else None,
                "finished_at": record.finished_at.isoformat() if record.finished_at else None,
            }

    @staticmethod
    def _objective_from_record(raw_objective: str) -> str:
        try:
            payload = json.loads(raw_objective)
        except (TypeError, json.JSONDecodeError):
            return raw_objective
        return str(
            payload.get("objective")
            or payload.get("workflow")
            or payload.get("type")
            or ""
        )

    async def list_tasks(self, status_filter: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        from sqlalchemy import select
        async with async_session() as session:
            stmt = select(AutoLoopTask).order_by(AutoLoopTask.created_at.desc()).limit(limit)
            if status_filter:
                stmt = stmt.where(AutoLoopTask.status == status_filter)
            result = await session.execute(stmt)
            records = result.scalars().all()
            return [
                {
                    "task_id": r.id,
                    "objective": self._objective_from_record(r.objective)[:100],
                    "status": r.status,
                    "progress": r.current_step,
                    "total_steps": r.max_steps,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]

    async def _run_task(self, task_id: str, task_type: str, payload: dict[str, Any]) -> None:
        async with self._semaphore:
            now = datetime.now(UTC)
            handler = self._handlers[task_type]

            async with async_session() as session:
                record = await session.get(AutoLoopTask, task_id)
                if record:
                    record.status = TaskStatus.RUNNING.value
                    record.started_at = now
                    record.heartbeat_at = now
                    await session.commit()

            try:
                async def _progress_cb(step: int, total: int, message: str = ""):
                    async with async_session() as session:
                        rec = await session.get(AutoLoopTask, task_id)
                        if rec:
                            rec.current_step = step
                            rec.max_steps = total
                            rec.heartbeat_at = datetime.now(UTC)
                            await session.commit()
                    await self._emit_progress(task_id, {"step": step, "total": total, "message": message})

                runtime_payload = {**payload, "_task_id": task_id}
                result = await handler(payload=runtime_payload, on_progress=_progress_cb)
                result_status = (
                    TaskStatus.FAILED.value
                    if isinstance(result, dict) and result.get("status") == TaskStatus.FAILED.value
                    else TaskStatus.COMPLETED.value
                )

                async with async_session() as session:
                    record = await session.get(AutoLoopTask, task_id)
                    if record:
                        record.status = result_status
                        record.result = result if isinstance(result, dict) else {"output": str(result)}
                        if result_status == TaskStatus.FAILED.value and isinstance(result, dict):
                            record.error = str(result.get("error", ""))[:500]
                        record.finished_at = datetime.now(UTC)
                        record.current_step = record.max_steps
                        await session.commit()

                await self._emit_progress(task_id, {"status": result_status, "result": result})

            except asyncio.CancelledError:
                async with async_session() as session:
                    record = await session.get(AutoLoopTask, task_id)
                    if record:
                        record.status = TaskStatus.CANCELLED.value
                        record.finished_at = datetime.now(UTC)
                        await session.commit()
                await self._emit_progress(task_id, {"status": "cancelled"})

            except Exception as exc:
                logger.error("task_failed", task_id=task_id, error=str(exc))
                async with async_session() as session:
                    record = await session.get(AutoLoopTask, task_id)
                    if record:
                        record.status = TaskStatus.FAILED.value
                        record.error = str(exc)[:500]
                        record.finished_at = datetime.now(UTC)
                        await session.commit()
                await self._emit_progress(task_id, {"status": "failed", "error": str(exc)})

    async def _emit_progress(self, task_id: str, data: dict) -> None:
        for cb in self._progress_callbacks:
            with suppress(Exception):
                await cb(task_id, data)


async def handle_agent_run(payload: dict[str, Any], on_progress) -> dict[str, Any]:
    """Execute an autonomous agent run with the given objective."""
    from app.core.agent_engine import AgentEngine
    from app.core.di import resolve as di_resolve
    objective = payload.get("objective", "")
    if not objective.strip():
        raise ValueError("objective is required")
    max_steps = int(payload.get("max_steps", 10))
    try:
        engine = di_resolve("AgentEngine")
    except KeyError:
        engine = AgentEngine()
    session = engine.create_session(
        agent_id="task-worker",
        user_id=str(payload.get("user_id", "system")),
        provider=str(payload.get("provider", "openai")),
        model_id=str(payload.get("model", "gpt-4o-mini")),
        api_key=str(payload.get("api_key", "")),
        base_url=payload.get("base_url"),
        system_prompt=str(payload.get("system_prompt", "")),
        tools=payload.get("tools") or [],
    )
    session.max_iterations = max_steps
    output: list[str] = []
    current_iteration = 0
    async for event in engine.run(session, objective):
        if event.type.value == "thinking":
            current_iteration = int(event.data.get("iteration", current_iteration))
            await on_progress(
                current_iteration,
                max_steps,
                f"Running iteration {current_iteration}",
            )
        elif event.type.value == "text":
            output.append(str(event.data.get("content", "")))
        elif event.type.value == "error":
            raise RuntimeError(str(event.data.get("error", "Agent execution failed")))
    completed_steps = max(current_iteration, 1)
    await on_progress(completed_steps, completed_steps, "Complete")
    return {
        "output": "".join(output),
        "tokens_used": session.metrics.total_tokens_used,
        "iterations": session.metrics.total_iterations,
    }


def _build_factory_plan(goal: str, skills: list[str]) -> list[dict[str, Any]]:
    """Build a safe fallback plan from selected capabilities."""
    steps: list[dict[str, Any]] = []
    if "web_search" in skills:
        steps.append({
            "action": "Research current evidence and constraints",
            "objective": f"Research reliable, current information needed to accomplish: {goal}",
            "tools": ["web_search"],
        })
    if "file_manager" in skills or "code_reviewer" in skills:
        steps.append({
            "action": "Inspect the existing project and identify the smallest correct change",
            "objective": f"Inspect the available project context and determine a concrete approach for: {goal}",
            "tools": ["read_file", "list_files"],
        })
    execution_tools = [
        tool
        for skill in skills
        for tool in _FACTORY_SKILL_TOOLS.get(skill, [])
        if tool not in {"web_search", "read_file", "list_files"}
    ]
    steps.append({
        "action": "Execute the goal and produce a verifiable result",
        "objective": goal,
        "tools": list(dict.fromkeys(execution_tools)),
    })
    return [
        {"step": index, "status": "pending", **step}
        for index, step in enumerate(steps, start=1)
    ]


def _parse_factory_plan(raw_plan: str, goal: str, skills: list[str]) -> list[dict[str, Any]]:
    """Validate planner output and constrain it to selected tools."""
    text = raw_plan.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1])
    parsed = json.loads(text)
    raw_steps = parsed.get("steps") if isinstance(parsed, dict) else parsed
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("Planner returned no steps")
    allowed_tools = {
        tool for skill in skills for tool in _FACTORY_SKILL_TOOLS.get(skill, [])
    }
    plan: list[dict[str, Any]] = []
    for index, raw_step in enumerate(raw_steps[:5], start=1):
        if not isinstance(raw_step, dict):
            raise ValueError("Planner returned an invalid step")
        action = str(raw_step.get("action", "")).strip()
        objective = str(raw_step.get("objective", action)).strip()
        if not action or not objective:
            raise ValueError("Planner step is missing an action or objective")
        requested_tools = raw_step.get("tools", [])
        tools = [
            str(tool) for tool in requested_tools
            if str(tool) in allowed_tools
        ] if isinstance(requested_tools, list) else []
        plan.append({
            "step": index,
            "status": "pending",
            "action": action,
            "objective": objective,
            "tools": list(dict.fromkeys(tools)),
        })
    return plan


_FACTORY_SKILL_TOOLS = {
    "code_executor": ["run_command"],
    "web_search": ["web_search"],
    "file_manager": ["read_file", "write_file", "list_files"],
    "data_analyzer": ["calculator"],
    "task_planner": [],
    "code_reviewer": ["read_file", "list_files"],
}


async def handle_factory_run(payload: dict[str, Any], on_progress) -> dict[str, Any]:
    """Run a planned, retryable multi-stage Agent Factory workflow."""
    task_id = str(payload["_task_id"])
    goal = str(payload.get("objective", "")).strip()
    if not goal:
        raise ValueError("objective is required")
    skills = [str(skill) for skill in payload.get("factory_skills", [])]
    await task_manager.emit_event(task_id, "factory_start", {"task_id": task_id})
    await task_manager.emit_event(task_id, "planning", {"message": "Creating execution plan"})
    agent_handler = task_manager._handlers["agent_run"]
    planner_payload = {
        **payload,
        "objective": (
            "Create a concise execution plan for the goal below. Return JSON only as "
            '{"steps":[{"action":"...","objective":"...","tools":["..."]}]}. '
            f"Use at most 5 steps and only these tools: {payload.get('tools', [])}.\n\n"
            f"Goal: {goal}"
        ),
        "tools": [],
        "max_steps": 3,
    }
    planner_payload.pop("_task_id", None)
    try:
        planner_result = await agent_handler(
            payload=planner_payload,
            on_progress=lambda *_: asyncio.sleep(0),
        )
        planner_output = (
            planner_result.get("output", "")
            if isinstance(planner_result, dict)
            else str(planner_result)
        )
        plan = _parse_factory_plan(planner_output, goal, skills)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        plan = _build_factory_plan(goal, skills)
        await task_manager.emit_event(task_id, "plan_fallback", {"reason": str(exc)})
    await task_manager.emit_event(task_id, "plan", {
        "steps": [
            {
                "step": step["step"],
                "action": step["action"],
                "status": "pending",
                **({"tool": step["tools"][0]} if step.get("tools") else {}),
            }
            for step in plan
        ]
    })

    results: list[dict[str, Any]] = []
    for index, step in enumerate(plan, start=1):
        step_id = f"{task_id}:{index}"
        await task_manager.emit_event(task_id, "task_start", {
            "task_id": step_id,
            "step": index,
            "description": step["action"],
        })
        step_payload = {
            **payload,
            "objective": step["objective"],
            "tools": step["tools"] or payload.get("tools", []),
            "max_steps": min(int(payload.get("max_steps", 10)), 6),
        }
        step_payload.pop("_task_id", None)
        last_error: Exception | None = None
        for attempt in range(1, 3):
            try:
                async def _step_progress(current: int, total: int, message: str = "", _step_id: str = step_id, _index: int = index) -> None:
                    await task_manager.emit_event(task_id, "progress", {
                        "task_id": _step_id,
                        "step": _index,
                        "current": current,
                        "total": total,
                        "message": message,
                    })

                result = await agent_handler(payload=step_payload, on_progress=_step_progress)
                output = result.get("output", "") if isinstance(result, dict) else str(result)
                results.append({"step": index, "action": step["action"], "output": output})
                await task_manager.emit_event(task_id, "task_complete", {
                    "task_id": step_id,
                    "step": index,
                    "result": output,
                })
                break
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    await task_manager.emit_event(task_id, "task_retry", {
                        "task_id": step_id,
                        "step": index,
                        "retries": attempt,
                        "error": str(exc),
                    })
                    await asyncio.sleep(0.5)
        else:
            error = str(last_error or "Step failed")
            await task_manager.emit_event(task_id, "task_failed", {
                "task_id": step_id,
                "step": index,
                "error": error,
            })
            raise RuntimeError(f"Factory step {index} failed: {error}")
        await on_progress(index, len(plan) + 1, step["action"])

    evidence = "\n\n".join(
        f"Step {item['step']} - {item['action']}:\n{item['output']}" for item in results
    )
    synthesis_payload = {
        **payload,
        "objective": (
            f"Produce the final answer for this goal:\n{goal}\n\n"
            f"Use these completed step results as evidence:\n{evidence}"
        ),
        "tools": [],
        "max_steps": 4,
    }
    synthesis_payload.pop("_task_id", None)
    try:
        synthesis = await agent_handler(payload=synthesis_payload, on_progress=lambda *_: asyncio.sleep(0))
        report = synthesis.get("output", "") if isinstance(synthesis, dict) else str(synthesis)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("factory_synthesis_failed", task_id=task_id, error=str(exc))
        report = evidence
    await on_progress(len(plan) + 1, len(plan) + 1, "Synthesis complete")
    await task_manager.emit_event(task_id, "synthesize", {"report": report})
    return {"output": report, "plan": plan, "steps": results}


async def handle_data_processing(payload: dict[str, Any], on_progress) -> dict[str, Any]:
    """Process data: transform, filter, aggregate."""
    data = payload.get("data", [])
    operation = payload.get("operation", "identity")
    total = len(data)
    results = []
    for i, item in enumerate(data):
        if operation == "uppercase" and isinstance(item, str):
            results.append(item.upper())
        elif operation == "lowercase" and isinstance(item, str):
            results.append(item.lower())
        elif operation == "reverse":
            results.append(item[::-1] if isinstance(item, str) else item)
        else:
            results.append(item)
        if (i + 1) % max(1, total // 20) == 0:
            await on_progress(i + 1, total, f"Processed {i+1}/{total}")
            await asyncio.sleep(0)
    await on_progress(total, total, "Complete")
    return {"processed": len(results), "results": results[:100]}


async def handle_workflow(payload: dict[str, Any], on_progress) -> dict[str, Any]:
    """Execute a multi-step workflow."""
    from app.multi_agent.flow import Flow
    workflow_name = payload.get("workflow", "default")
    params = payload.get("params", {})
    flow = Flow(name=workflow_name)
    result = await flow.execute(params=params, on_progress=on_progress)
    return result


task_manager = TaskManager(max_workers=3)
task_manager.register("agent_run", handle_agent_run)
task_manager.register("factory_run", handle_factory_run)
task_manager.register("data_processing", handle_data_processing)
task_manager.register("workflow", handle_workflow)


async def run_standalone_worker():
    """Run as standalone worker process."""
    logger.info("standalone_worker_started")
    while True:
        async with async_session() as session:
            from sqlalchemy import select
            stmt = select(AutoLoopTask).where(
                AutoLoopTask.status == TaskStatus.PENDING.value
            ).order_by(AutoLoopTask.created_at).limit(5)
            result = await session.execute(stmt)
            pending = result.scalars().all()
            for record in pending:
                try:
                    obj = json.loads(record.objective)
                    task_type = obj.pop("type", "agent_run")
                    if task_type in task_manager._handlers:
                        await task_manager.submit(task_type, obj)
                except Exception as exc:
                    logger.error("enqueue_failed", task_id=record.id, error=str(exc))
        await asyncio.sleep(5)
