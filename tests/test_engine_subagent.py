"""Tests for subagent lifecycle manager."""

import asyncio

import pytest

from app.core.engine.subagent import (
    SubagentManager,
    SubagentSpec,
    SubagentState,
    SubagentUsage,
)


class TestSubagentManager:
    @pytest.mark.asyncio
    async def test_spawn_success(self) -> None:
        manager = SubagentManager()
        spec = SubagentSpec(description="test task", timeout_seconds=5.0)

        async def runner(spec: SubagentSpec) -> tuple[str, SubagentUsage]:
            return "done", SubagentUsage(tokens_in=10, tokens_out=20)

        record = await manager.spawn(spec, runner)
        assert record.state == SubagentState.COMPLETED
        assert record.result == "done"
        assert record.usage.tokens_in == 10

    @pytest.mark.asyncio
    async def test_depth_limit(self) -> None:
        manager = SubagentManager(depth_limit=2)
        spec = SubagentSpec(description="deep task", depth=3)

        async def runner(spec: SubagentSpec) -> tuple[str, SubagentUsage]:
            return "done", SubagentUsage()

        record = await manager.spawn(spec, runner)
        assert record.state == SubagentState.FAILED
        assert "Depth limit" in record.error

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        manager = SubagentManager()
        spec = SubagentSpec(description="slow task", timeout_seconds=0.1)

        async def runner(spec: SubagentSpec) -> tuple[str, SubagentUsage]:
            await asyncio.sleep(10)
            return "done", SubagentUsage()

        record = await manager.spawn(spec, runner)
        assert record.state == SubagentState.TIMED_OUT

    @pytest.mark.asyncio
    async def test_concurrency_limit(self) -> None:
        manager = SubagentManager(concurrency_limit=1)
        spec1 = SubagentSpec(description="task 1", timeout_seconds=5.0)
        spec2 = SubagentSpec(description="task 2", timeout_seconds=5.0)

        async def runner(spec: SubagentSpec) -> tuple[str, SubagentUsage]:
            await asyncio.sleep(0.05)
            return spec.description, SubagentUsage()

        r1, r2 = await asyncio.gather(
            manager.spawn(spec1, runner),
            manager.spawn(spec2, runner),
        )
        assert r1.state == SubagentState.COMPLETED
        assert r2.state == SubagentState.COMPLETED

    @pytest.mark.asyncio
    async def test_cancel(self) -> None:
        manager = SubagentManager()
        spec = SubagentSpec(description="cancel me", timeout_seconds=10.0)

        async def runner(spec: SubagentSpec) -> tuple[str, SubagentUsage]:
            await asyncio.sleep(10)
            return "done", SubagentUsage()

        # Start task, then cancel
        task = asyncio.create_task(manager.spawn(spec, runner))
        await asyncio.sleep(0.05)
        cancelled = manager.cancel(spec.task_id)
        assert cancelled is True

        record = await task
        assert record.state == SubagentState.CANCELLED

    @pytest.mark.asyncio
    async def test_cascade_cancel(self) -> None:
        manager = SubagentManager(enable_cascade_cancel=True)
        parent_spec = SubagentSpec(description="parent", timeout_seconds=10.0)
        child_spec = SubagentSpec(description="child", parent_id=parent_spec.task_id, timeout_seconds=10.0)

        async def runner(spec: SubagentSpec) -> tuple[str, SubagentUsage]:
            await asyncio.sleep(10)
            return "done", SubagentUsage()

        # Spawn parent first
        parent_task = asyncio.create_task(manager.spawn(parent_spec, runner))
        await asyncio.sleep(0.05)

        # Spawn child
        child_task = asyncio.create_task(manager.spawn(child_spec, runner))
        await asyncio.sleep(0.05)

        # Cancel parent should cascade
        manager.cancel(parent_spec.task_id)

        parent = await parent_task
        child = await child_task
        assert parent.state == SubagentState.CANCELLED
        assert child.state == SubagentState.CANCELLED

    def test_get_record(self) -> None:
        manager = SubagentManager()
        spec = SubagentSpec(description="test")
        manager._records[spec.task_id] = manager._records.get(spec.task_id, None) or type("R", (), {
            "spec": spec, "state": SubagentState.PENDING
        })()

    @pytest.mark.asyncio
    async def test_get_active_runs(self) -> None:
        manager = SubagentManager()
        spec = SubagentSpec(description="active task", timeout_seconds=10.0)

        async def runner(spec: SubagentSpec) -> tuple[str, SubagentUsage]:
            await asyncio.sleep(0.1)
            return "done", SubagentUsage()

        task = asyncio.create_task(manager.spawn(spec, runner))
        await asyncio.sleep(0.02)
        active = manager.get_active_runs()
        assert len(active) >= 1
        await task

    @pytest.mark.asyncio
    async def test_get_stats(self) -> None:
        manager = SubagentManager()
        spec = SubagentSpec(description="task", timeout_seconds=5.0)

        async def runner(spec: SubagentSpec) -> tuple[str, SubagentUsage]:
            return "done", SubagentUsage(tokens_in=100, tokens_out=200, cost_usd=0.001)

        await manager.spawn(spec, runner)
        stats = manager.get_stats()
        assert stats["total"] == 1
        assert stats["total_tokens"] == 300
        assert stats["depth_limit"] == 3
        assert stats["concurrency_limit"] == 5


class TestSubagentSpec:
    def test_auto_task_id(self) -> None:
        spec = SubagentSpec()
        assert len(spec.task_id) == 12

    def test_custom_task_id(self) -> None:
        spec = SubagentSpec(task_id="custom-123")
        assert spec.task_id == "custom-123"


class TestSubagentUsage:
    def test_to_dict(self) -> None:
        usage = SubagentUsage(tokens_in=100, tokens_out=200, cost_usd=0.001, tool_calls=3, duration_ms=1500.0)
        d = usage.to_dict()
        assert d["tokens_in"] == 100
        assert d["tokens_out"] == 200
        assert d["cost_usd"] == 0.001
        assert d["tool_calls"] == 3
