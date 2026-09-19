"""Tests for collaboration deadlock detection and its resolver integration."""

from __future__ import annotations

import pytest

from app.core.collaboration.deadlock import (
    deadlocked_task_ids,
    detect_deadlock,
    topological_order,
)


class TestDetectDeadlock:
    """Pure unit tests for cycle detection."""

    def test_no_cycle_returns_empty(self) -> None:
        assert detect_deadlock({"a": [], "b": ["a"], "c": ["b"]}) == []
        assert detect_deadlock([("b", "a"), ("c", "b")]) == []

    def test_simple_cycle_is_detected(self) -> None:
        cycles = detect_deadlock({"a": ["b"], "b": ["a"]})
        assert len(cycles) == 1
        assert set(cycles[0]) == {"a", "b"}

    def test_three_node_cycle_is_detected(self) -> None:
        cycles = detect_deadlock({"a": ["c"], "b": ["a"], "c": ["b"]})
        assert len(cycles) == 1
        assert set(cycles[0]) == {"a", "b", "c"}

    def test_edge_list_form(self) -> None:
        cycles = detect_deadlock([("a", "b"), ("b", "a"), ("b", "c")])
        assert len(cycles) == 1
        assert set(cycles[0]) == {"a", "b"}

    def test_self_loop_is_a_cycle(self) -> None:
        cycles = detect_deadlock({"a": ["a"], "b": []})
        assert len(cycles) == 1
        assert cycles[0] == ["a", "a"]

    def test_parallel_cycles_reported_once(self) -> None:
        graph = {"a": ["b"], "b": ["a"], "x": ["y"], "y": ["x"]}
        cycles = detect_deadlock(graph)
        assert len(cycles) == 2

    def test_empty_input(self) -> None:
        assert detect_deadlock({}) == []
        assert detect_deadlock([]) == []

    def test_cycle_with_dependents(self) -> None:
        cycles = detect_deadlock({"a": ["c"], "b": ["a"], "c": ["b"], "d": ["b"]})
        assert len(cycles) == 1
        assert set(cycles[0]) == {"a", "b", "c"}
        assert deadlocked_task_ids({"a": ["c"], "b": ["a"], "c": ["b"], "d": ["b"]}) == {"a", "b", "c"}


class TestTopologicalOrder:
    """Unit tests for dependency-level ordering."""

    def test_levels_for_acyclic_graph(self) -> None:
        levels = topological_order({"a": [], "b": ["a"], "c": ["a", "b"]})
        assert levels == [["a"], ["b"], ["c"]]

    def test_external_dependency_treated_as_satisfied(self) -> None:
        levels = topological_order({"b": ["external"], "c": ["b"]})
        assert levels == [["b"], ["c"]]

    def test_cycle_nodes_and_dependents_are_omitted(self) -> None:
        graph = {"a": ["c"], "b": ["a"], "c": ["b"], "d": ["b"], "e": ["d"]}
        levels = topological_order(graph)
        scheduled = {node for level in levels for node in level}
        assert scheduled == set()

    def test_partial_cycle_blocks_only_affected_path(self) -> None:
        graph = {"a": ["b"], "b": ["a"], "free": []}
        levels = topological_order(graph)
        assert levels == [["free"]]


@pytest.mark.asyncio
async def test_run_group_tasks_executes_acyclic_dependencies_in_order() -> None:
    """Resolver integration: acyclic tasks run on the success path."""
    from app.core.collaboration.base import GroupCollaborationEngine
    from app.storage import async_session
    from app.storage.models_groups import AgentGroup, AgentGroupTask

    group_id = "dl-acyclic-group"
    async with async_session() as db:
        db.add(AgentGroup(id=group_id, name="dl-acyclic", user_id="default-user"))
        db.add(AgentGroupTask(id="dl-t1", group_id=group_id, description="t1", status="pending", dependencies=[]))
        db.add(
            AgentGroupTask(id="dl-t2", group_id=group_id, description="t2", status="pending", dependencies=["dl-t1"])
        )
        db.add(
            AgentGroupTask(id="dl-t3", group_id=group_id, description="t3", status="pending", dependencies=["dl-t2"])
        )
        await db.commit()

    engine = GroupCollaborationEngine(model_registry=object(), tool_registry=object())
    calls: list[str] = []

    async def fake_run(task, group, context_data):
        calls.append(task.id)

    engine._run_single_task_in_dag = fake_run

    try:
        result = await engine.run_group_tasks(group_id)
        assert result["status"] == "completed"
        assert calls == ["dl-t1", "dl-t2", "dl-t3"]
    finally:
        async with async_session() as db:
            for tid in ("dl-t1", "dl-t2", "dl-t3"):
                row = await db.get(AgentGroupTask, tid)
                if row:
                    await db.delete(row)
            group = await db.get(AgentGroup, group_id)
            if group:
                await db.delete(group)
            await db.commit()


@pytest.mark.asyncio
async def test_run_group_tasks_reports_deadlock_and_skips_execution() -> None:
    """Resolver integration: a full cycle aborts with a deadlock result."""
    from app.core.collaboration.base import GroupCollaborationEngine
    from app.storage import async_session
    from app.storage.models_groups import AgentGroup, AgentGroupTask

    group_id = "dl-cycle-group"
    async with async_session() as db:
        db.add(AgentGroup(id=group_id, name="dl-cycle", user_id="default-user"))
        db.add(
            AgentGroupTask(id="dl-c1", group_id=group_id, description="c1", status="pending", dependencies=["dl-c2"])
        )
        db.add(
            AgentGroupTask(id="dl-c2", group_id=group_id, description="c2", status="pending", dependencies=["dl-c1"])
        )
        await db.commit()

    engine = GroupCollaborationEngine(model_registry=object(), tool_registry=object())
    ran: list[str] = []

    async def fake_run(task, group, context_data):
        ran.append(task.id)

    engine._run_single_task_in_dag = fake_run

    try:
        result = await engine.run_group_tasks(group_id)
        assert result["status"] == "deadlock"
        assert "error" in result
        assert ran == []
    finally:
        async with async_session() as db:
            for tid in ("dl-c1", "dl-c2"):
                row = await db.get(AgentGroupTask, tid)
                if row:
                    await db.delete(row)
            group = await db.get(AgentGroup, group_id)
            if group:
                await db.delete(group)
            await db.commit()


@pytest.mark.asyncio
async def test_run_group_tasks_skips_only_blocked_tasks() -> None:
    """Resolver integration: unaffected tasks still run when only some are blocked."""
    from app.core.collaboration.base import GroupCollaborationEngine
    from app.storage import async_session
    from app.storage.models_groups import AgentGroup, AgentGroupTask

    group_id = "dl-partial-group"
    async with async_session() as db:
        db.add(AgentGroup(id=group_id, name="dl-partial", user_id="default-user"))
        db.add(
            AgentGroupTask(id="dl-p1", group_id=group_id, description="p1", status="pending", dependencies=["dl-p2"])
        )
        db.add(
            AgentGroupTask(id="dl-p2", group_id=group_id, description="p2", status="pending", dependencies=["dl-p1"])
        )
        db.add(AgentGroupTask(id="dl-p3", group_id=group_id, description="p3", status="pending", dependencies=[]))
        await db.commit()

    engine = GroupCollaborationEngine(model_registry=object(), tool_registry=object())
    ran: list[str] = []

    async def fake_run(task, group, context_data):
        ran.append(task.id)

    engine._run_single_task_in_dag = fake_run

    try:
        result = await engine.run_group_tasks(group_id)
        assert result["status"] == "completed"
        assert ran == ["dl-p3"]
    finally:
        async with async_session() as db:
            for tid in ("dl-p1", "dl-p2", "dl-p3"):
                row = await db.get(AgentGroupTask, tid)
                if row:
                    await db.delete(row)
            group = await db.get(AgentGroup, group_id)
            if group:
                await db.delete(group)
            await db.commit()
