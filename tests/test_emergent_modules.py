"""Tests for the fourth-generation emergent modules (A-D) and snapshots."""
from __future__ import annotations

import pytest

from app.core.emergent.autodiscovery import AutodiscoveryConfig, AutodiscoveryEngine
from app.core.emergent.goal_centered import GoalCenteredPlanner, GoalState
from app.core.emergent.meta_agent import MetaAgent, MetaProposal
from app.core.emergent.snapshot import StructuralSnapshotManager
from app.core.emergent.swarm import (
    DEFAULT_BEES,
    IntentParseBee,
    SwarmCoordinator,
    SwarmTask,
)
from app.core.event_bus import EventBus
from app.core.metacognition.capability_discovery import CapabilityDiscovery, ComposedCapability
from app.core.sandbox import SandboxConfig, SandboxExecutor


def _registry(tmp_path) -> CapabilityDiscovery:
    return CapabilityDiscovery(storage_path=str(tmp_path / "caps.json"))


# --- Module A: Autodiscovery ---


@pytest.mark.asyncio
async def test_autodiscovery_discards_low_success(tmp_path):
    reg = _registry(tmp_path)
    sb = SandboxExecutor(config=SandboxConfig(timeout_seconds=2))
    eng = AutodiscoveryEngine(
        registry=reg, sandbox=sb,
        config=AutodiscoveryConfig(sandbox_steps_max=6, success_threshold=0.8),
    )
    cand = await eng.explore("validate something", ["definitely_not_a_command_xyz"])
    assert cand is None
    assert eng.list_pending() == []


@pytest.mark.asyncio
async def test_autodiscovery_commit_requires_snapshot(tmp_path):
    reg = _registry(tmp_path)
    sb = SandboxExecutor(config=SandboxConfig(timeout_seconds=2))

    async def bad_snap():
        return None

    eng = AutodiscoveryEngine(
        registry=reg, sandbox=sb,
        config=AutodiscoveryConfig(
            sandbox_steps_max=4, success_threshold=0.0,
            approval_required=False, snapshot_fn=bad_snap,
        ),
    )
    cand = await eng.explore("collect info", ["ls"])
    assert cand is not None
    composed = await eng.commit(cand.name)
    assert composed is None
    assert reg.get_capability(cand.name) is None


@pytest.mark.asyncio
async def test_autodiscovery_full_commit_cycle(tmp_path):
    reg = _registry(tmp_path)
    sb = SandboxExecutor(config=SandboxConfig(timeout_seconds=3))

    async def snap():
        return "snap_a"

    eng = AutodiscoveryEngine(
        registry=reg, sandbox=sb,
        config=AutodiscoveryConfig(
            sandbox_steps_max=8, success_threshold=0.8,
            approval_required=True, snapshot_fn=snap,
        ),
    )
    cand = await eng.explore("analyze report data", ["ls -la", "pwd", "echo hello"])
    assert cand is not None
    assert cand.success_rate >= 0.8
    # Unapproved cannot commit
    assert await eng.commit(cand.name) is None
    assert await eng.request_approval(cand.name)
    composed = await eng.commit(cand.name)
    assert composed is not None
    assert reg.get_capability(cand.name) is not None


# --- Module B: Meta-Agent ---


@pytest.mark.asyncio
async def test_meta_agent_propose_apply_rollback():
    bus = EventBus()
    applied: list[str] = []
    rolled_back: list[str] = []

    async def snap():
        return "snap_b"

    async def apply_fn(p: MetaProposal):
        applied.append(p.summary)

    async def rollback_fn(sid: str):
        rolled_back.append(sid)

    ma = MetaAgent(
        event_bus=bus, snapshot_fn=snap,
        apply_fn=apply_fn, rollback_fn=rollback_fn,
    )
    await ma.start_monitoring()
    try:
        for _ in range(4):
            await bus.publish("tool_error", {"tool": "web_search", "error": "timeout"})
        await bus.publish("session_error", {"error": "crash"})
        assert len(ma.list_events()) == 5

        p = await ma.propose()
        assert p is not None
        assert p.kind == "loop_guard"
        assert await ma.apply(p) is False  # unapproved
        assert ma.approve(p)
        assert await ma.apply(p)
        assert applied == [p.summary]
        assert p.snapshot_id == "snap_b"
        assert await ma.rollback(p.snapshot_id)
        assert rolled_back == ["snap_b"]
    finally:
        await ma.stop_monitoring()
    assert bus.get_history(event_type="tool_error", limit=1)  # type subscription removed


@pytest.mark.asyncio
async def test_meta_agent_no_proposal_when_healthy():
    bus = EventBus()
    ma = MetaAgent(event_bus=bus)
    await ma.start_monitoring()
    try:
        await bus.publish("tool_result", {"tool": "ls", "output": "ok"})
        await bus.publish("session_complete", {"ok": True})
        assert await ma.propose() is None
    finally:
        await ma.stop_monitoring()


# --- Module C: Goal-Centered ---


@pytest.mark.asyncio
async def test_goal_planner_registry_first(tmp_path):
    reg = _registry(tmp_path)
    reg.register(ComposedCapability(
        name="collect_reports", description="gather and collect reports",
        tool_chain=[{"tool": "web_search", "purpose": "search"}],
        inputs={}, output_description="reports",
    ))
    planner = GoalCenteredPlanner(registry=reg)
    res = await planner.plan(GoalState(), "collect reports now")
    assert res is not None
    assert res.source == "registry"


@pytest.mark.asyncio
async def test_goal_planner_simulation_and_cache(tmp_path):
    reg = _registry(tmp_path)

    async def snap():
        return "snap_c"

    planner = GoalCenteredPlanner(registry=reg, snapshot_fn=snap)
    res = await planner.plan(GoalState(), "analyze customer data")
    assert res is not None
    assert res.source == "simulation"
    cached = await planner.cache_simulation("analyze customer data", res.steps)
    assert cached is not None
    res2 = await planner.plan(GoalState(), "analyze customer data")
    assert res2.source == "registry"


@pytest.mark.asyncio
async def test_goal_planner_timeout_falls_back(tmp_path):
    reg = _registry(tmp_path)
    planner = GoalCenteredPlanner(registry=reg, max_seconds=10.0)
    res = await planner.plan(GoalState(), "whatever", max_seconds=0.0)
    assert res is None  # caller falls back to traditional tools


# --- Module D: Swarm ---


@pytest.mark.asyncio
async def test_swarm_normal_run():
    bus = EventBus()
    coord = SwarmCoordinator(event_bus=bus, bees=DEFAULT_BEES)
    results = await coord.run_subtask(SwarmTask(id="t1", objective="analyze report data", scope="subtask"))
    assert results["intent_parser"]["intent"] == "analyze"
    assert results["state_validator"]["valid"] is True
    assert results["safety_checker"]["safe"] is True
    assert results["device_executor"]["executed"] is True


@pytest.mark.asyncio
async def test_swarm_bee_degradation():
    class CrashBee:
        name = "crashy"

        async def handle(self, task, bus):
            raise RuntimeError("boom")

    bus = EventBus()
    coord = SwarmCoordinator(event_bus=bus, bees=DEFAULT_BEES)
    coord.register_bee(CrashBee())
    results = await coord.run_subtask(SwarmTask(id="t2", objective="safe task"))
    assert results["crashy"] == {"degraded": True}
    assert "crashy" in coord.degraded_bees
    assert "crashy" not in coord.active_bees()
    assert results["device_executor"]["executed"] is True


@pytest.mark.asyncio
async def test_swarm_dynamic_activation():
    coord = SwarmCoordinator(bees=[IntentParseBee()])
    assert "intent_parser" in coord.active_bees()
    assert coord.deactivate("intent_parser")
    assert "intent_parser" not in coord.active_bees()
    assert coord.activate("intent_parser")
    assert "intent_parser" in coord.active_bees()


@pytest.mark.asyncio
async def test_swarm_safety_checker_blocks_high_risk():
    coord = SwarmCoordinator(bees=[IntentParseBee()])
    coord.register_bee(DEFAULT_BEES[3])  # safety_checker
    results = await coord.run_subtask(SwarmTask(id="t3", objective="rm -rf /data"))
    assert results["safety_checker"]["safe"] is False


# --- Snapshots ---


@pytest.mark.asyncio
async def test_snapshot_rollback(tmp_path):
    state = {"registry": {"a": 1}}
    mgr = StructuralSnapshotManager(
        storage_dir=str(tmp_path / "snaps"),
        registry_dump=lambda: dict(state["registry"]),
        registry_restore=lambda p: state.__setitem__("registry", dict(p)),
    )
    sid = await mgr.capture("before")
    state["registry"]["b"] = 2
    assert await mgr.rollback(sid)
    assert state["registry"] == {"a": 1}


@pytest.mark.asyncio
async def test_snapshot_prune(tmp_path):
    mgr = StructuralSnapshotManager(storage_dir=str(tmp_path / "snaps"), keep_last=3)
    sids = [await mgr.capture(f"v{i}") for i in range(5)]
    assert len(mgr.list_snapshots()) == 3
    assert all(s["snapshot_id"] != sids[0] for s in mgr.list_snapshots())
    assert all(s["snapshot_id"] != sids[1] for s in mgr.list_snapshots())


@pytest.mark.asyncio
async def test_snapshot_rollback_missing(tmp_path):
    mgr = StructuralSnapshotManager(storage_dir=str(tmp_path / "snaps"))
    assert await mgr.rollback("snap_nonexistent") is False
