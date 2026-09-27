"""Crew scheduling: parallel fan-out, concurrency cap, failure isolation.

``Crew.execute`` used to await one task at a time in a ``for`` loop, so agents
never overlapped. It now runs the crew's tasks as a single bounded wave, the way
LangGraph runs one super-step and AutoGen's GraphFlow fans out and joins. These
tests pin the properties that make that safe: real overlap, a ceiling on
in-flight tasks, one failure not sinking the crew, and a deterministic merge
order regardless of which task finished first.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.core import AgentEvent, AgentEventType
from app.multi_agent import AgentRole, AgentTask, TaskStatus
from app.multi_agent.crew import DEFAULT_MAX_CONCURRENCY, Crew


class _RecordingEngine:
    """Stand-in for AgentEngine that records concurrency while it works.

    ``run`` holds the event loop for ``delay`` seconds so an overlapping
    implementation shows up as ``peak > 1`` in the counters, and appends its
    system prompt per call so tests can inspect what each task saw.
    """

    def __init__(self, delay: float = 0.05, fail_task_ids: set[str] | None = None) -> None:
        self.delay = delay
        self.fail_task_ids = fail_task_ids or set()
        self.running = 0
        self.peak = 0
        self.calls: list[str] = []
        self.messages: list[str] = []
        self.system_prompts: list[str] = []
        self.session_ids: list[str] = []
        self._counter = 0

    def create_session(self, **kwargs: Any) -> str:
        self._counter += 1
        session_id = f"session-{self._counter}"
        self.session_ids.append(session_id)
        self.system_prompts.append(kwargs.get("system_prompt", ""))
        return session_id

    async def run(self, session: str, message: str):
        self.calls.append(session)
        self.messages.append(message)
        self.running += 1
        self.peak = max(self.peak, self.running)
        try:
            await asyncio.sleep(self.delay)
            yield AgentEvent(type=AgentEventType.THINKING, data={})
            yield AgentEvent(type=AgentEventType.TEXT, data={"content": f"out-{session}"})
            yield AgentEvent(type=AgentEventType.DONE, data={})
        finally:
            self.running -= 1


def _agent(name: str) -> AgentRole:
    return AgentRole(name=name, role=f"{name} role", goal=f"{name} goal", backstory=f"{name} story")


def _task(task_id: str, agent_name: str = "alpha") -> AgentTask:
    return AgentTask(
        id=task_id,
        agent_name=agent_name,
        description=f"work item {task_id}",
        expected_output=f"result of {task_id}",
    )


async def test_tasks_of_a_crew_run_concurrently() -> None:
    """Three tasks must overlap; the old sequential loop peaked at one."""
    engine = _RecordingEngine(delay=0.05)
    tasks = [_task("t1"), _task("t2"), _task("t3")]
    crew = Crew(agents=[_agent("alpha")], tasks=tasks, engine=engine, process="parallel")

    output = await crew.execute()

    assert engine.peak == 3
    assert [t.status for t in tasks] == [TaskStatus.COMPLETED] * 3
    assert len(output.results) == 3


async def test_concurrency_is_capped_by_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Six tasks with a cap of two must never have three in flight."""
    monkeypatch.setenv("CLIMBER_CREW_MAX_CONCURRENCY", "2")
    engine = _RecordingEngine(delay=0.02)
    tasks = [_task(f"t{i}") for i in range(6)]
    crew = Crew(agents=[_agent("alpha")], tasks=tasks, engine=engine, process="parallel")

    await crew.execute()

    assert engine.peak == 2


async def test_concurrency_can_be_capped_per_crew() -> None:
    """A crew-local cap takes precedence over the environment default."""
    engine = _RecordingEngine(delay=0.02)
    tasks = [_task(f"local-{i}") for i in range(4)]
    crew = Crew(
        agents=[_agent("alpha")], tasks=tasks, engine=engine, max_concurrency=1, process="parallel"
    )

    await crew.execute()

    assert engine.peak == 1


async def test_empty_crew_returns_a_stable_output() -> None:
    """An empty registration is explicit and consumes no execution budget."""
    output = await Crew(agents=[], tasks=[], engine=None).execute()

    assert output.results == []
    assert output.total_iterations == 0
    assert output.final_output == "Crew has no tasks configured"


async def test_sequential_process_preserves_order_and_context() -> None:
    """The default process chains each completed task into the next prompt."""
    engine = _RecordingEngine(delay=0.0)
    tasks = [_task("t1"), _task("t2")]
    crew = Crew(agents=[_agent("alpha")], tasks=tasks, engine=engine)

    output = await crew.execute()

    assert engine.peak == 1
    assert [entry["task_id"] for entry in output.results] == ["t1", "t2"]
    assert "out-session-1" in engine.system_prompts[1]
    assert output.final_output == "out-session-2"


async def test_sequential_failure_isolated_and_later_tasks_run() -> None:
    """A failed task does not prevent later ordered tasks from running."""
    tasks = [_task("t1"), _task("t2"), _task("t3")]

    class _ExplodingEngine(_RecordingEngine):
        async def run(self, session: str, message: str):
            if "work item t2" in message:
                raise RuntimeError("upstream 429")
            async for event in super().run(session, message):
                yield event

    output = await Crew(agents=[_agent("alpha")], tasks=tasks, engine=_ExplodingEngine()).execute()

    assert tasks[1].status == TaskStatus.FAILED
    assert "upstream 429" in tasks[1].error
    assert [entry["task_id"] for entry in output.results] == ["t1", "t3"]
    assert output.total_iterations == 3


def test_invalid_process_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"sequential.*parallel"):
        Crew(agents=[], tasks=[], engine=None, process="round_robin")


async def test_a_broken_cap_value_falls_back_to_the_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A nonsense or non-positive cap must not disable the ceiling."""
    for raw in ("not-a-number", "0", "-3"):
        monkeypatch.setenv("CLIMBER_CREW_MAX_CONCURRENCY", raw)
        engine = _RecordingEngine(delay=0.01)
        task_count = DEFAULT_MAX_CONCURRENCY + 1
        tasks = [_task(f"{raw}-{i}") for i in range(task_count)]
        crew = Crew(agents=[_agent("alpha")], tasks=tasks, engine=engine, process="parallel")

        await crew.execute()

        assert engine.peak == DEFAULT_MAX_CONCURRENCY, raw


async def test_one_failing_task_does_not_sink_the_crew() -> None:
    """A raising task is marked FAILED; its siblings still produce results."""
    tasks = [_task("t1"), _task("t2"), _task("t3")]

    class _ExplodingEngine(_RecordingEngine):
        async def run(self, session: str, message: str):
            if message and "work item t2" in message:
                raise RuntimeError("upstream 429")
            async for event in super().run(session, message):
                yield event

    engine = _ExplodingEngine(delay=0.01)
    crew = Crew(agents=[_agent("alpha")], tasks=tasks, engine=engine, process="parallel")

    output = await crew.execute()

    assert tasks[1].status == TaskStatus.FAILED
    assert "upstream 429" in tasks[1].error
    assert tasks[0].status == TaskStatus.COMPLETED
    assert tasks[2].status == TaskStatus.COMPLETED
    assert [entry["task_id"] for entry in output.results] == ["t1", "t3"]


async def test_results_merge_in_declaration_order_not_completion_order() -> None:
    """The last declared task is the final output even if it finishes first."""
    tasks = [_task("t1"), _task("t2"), _task("t3")]
    delays = {"t1": 0.06, "t2": 0.03, "t3": 0.0}

    class _StaggeredEngine(_RecordingEngine):
        async def run(self, session: str, message: str):
            for task_id, delay in delays.items():
                if f"work item {task_id}" in message:
                    self.delay = delay
                    break
            async for event in super().run(session, message):
                yield event

    engine = _StaggeredEngine()
    crew = Crew(agents=[_agent("alpha")], tasks=tasks, engine=engine, process="parallel")

    output = await crew.execute()

    assert [entry["task_id"] for entry in output.results] == ["t1", "t2", "t3"]
    assert output.final_output == "out-session-3"
    assert output.total_iterations == 3


async def test_parallel_tasks_share_only_the_dispatch_context() -> None:
    """No task may see a sibling's output; every task sees the task plan."""
    prompts: dict[str, str] = {}

    class _PromptCapturingEngine(_RecordingEngine):
        def create_session(self, **kwargs: Any) -> str:
            self._counter += 1
            prompts[f"call-{self._counter}"] = kwargs.get("system_prompt", "")
            return f"session-{self._counter}"

    tasks = [_task("t1"), _task("t2")]
    engine = _PromptCapturingEngine(delay=0.02)
    crew = Crew(agents=[_agent("alpha")], tasks=tasks, engine=engine, process="parallel")

    output = await crew.execute()

    assert len(prompts) == 2
    for prompt in prompts.values():
        assert "## Task Plan" in prompt
        assert "work item t1" in prompt
        assert "out-session-" not in prompt
    assert "out-session-" in output.final_output


async def test_two_tasks_of_the_same_agent_get_their_own_session() -> None:
    """AgentEngine locks per session id, so a shared session would be rejected."""
    engine = _RecordingEngine(delay=0.02)
    tasks = [_task("t1", agent_name="alpha"), _task("t2", agent_name="alpha")]
    crew = Crew(agents=[_agent("alpha")], tasks=tasks, engine=engine, process="parallel")

    await crew.execute()

    assert engine.peak == 2
    assert len(set(engine.session_ids)) == 2


async def test_a_task_without_an_agent_fails_without_spending_budget() -> None:
    """An unroutable task never reaches the engine, so it costs no iteration."""
    engine = _RecordingEngine(delay=0.01)
    orphan = _task("t0", agent_name="ghost")
    real = _task("t1", agent_name="alpha")
    crew = Crew(
        agents=[_agent("alpha")],
        tasks=[orphan, real],
        engine=engine,
        max_iterations=1,
        process="parallel",
    )

    output = await crew.execute()

    assert orphan.status == TaskStatus.FAILED
    assert "ghost" in orphan.error
    assert real.status == TaskStatus.COMPLETED
    assert engine.calls == ["session-1"]
    assert output.total_iterations == 1


async def test_tasks_past_the_iteration_budget_stay_pending() -> None:
    """The budget truncates the wave; the tail is left untouched."""
    engine = _RecordingEngine(delay=0.01)
    tasks = [_task("t1"), _task("t2"), _task("t3")]
    crew = Crew(
        agents=[_agent("alpha")], tasks=tasks, engine=engine, max_iterations=2, process="parallel"
    )

    output = await crew.execute()

    assert [t.status for t in tasks] == [
        TaskStatus.COMPLETED,
        TaskStatus.COMPLETED,
        TaskStatus.PENDING,
    ]
    assert output.total_iterations == 2
    assert len(output.results) == 2


async def test_emergency_stop_short_circuits_before_any_task_runs() -> None:
    """The kill switch is checked before the fan-out, not inside it."""
    from app.core.observability import emergency_stop as es

    manager = es.EmergencyStopManager(db_path=":memory:")
    manager.activate(reason="test", triggered_by="tester")
    es.set_emergency_stop(manager)
    try:
        engine = _RecordingEngine(delay=0.01)
        tasks = [_task("t1"), _task("t2")]
        crew = Crew(agents=[_agent("alpha")], tasks=tasks, engine=engine)

        output = await crew.execute()
    finally:
        es.set_emergency_stop(None)

    assert engine.calls == []
    assert all(task.status == TaskStatus.FAILED for task in tasks)
    assert output.results == []
    assert "Emergency stop" in output.final_output
    assert output.total_iterations == 0
