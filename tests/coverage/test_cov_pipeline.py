"""Coverage tests for app.core.engine.pipeline."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.core import AgentEventType
from app.core.engine import pipeline as pipeline_mod
from app.core.engine.pipeline import (
    EnginePipelineError,
    RoutePlan,
    StepResult,
    TurnContext,
    build_pipeline_event,
    run_pipeline,
)


def _ctx(**kwargs: Any) -> TurnContext:
    base = {
        "message": "hello world",
        "session_id": "s1",
        "model": "m1",
        "provider": "p1",
        "api_key": "k",
    }
    base.update(kwargs)
    return TurnContext(**base)


def test_route_plan_to_dict_rounds_and_serializes() -> None:
    plan = RoutePlan(
        target_tier="C2",
        model="gpt",
        provider="openai",
        confidence=0.123456,
        probabilities={"C2": 0.9},
        savings_pct=12.3456,
        fallback_reason="cheap",
        route_source="ensemble",
        latency_ms=1.239,
    )
    data = plan.to_dict()
    assert data["target_tier"] == "C2"
    assert data["confidence"] == 0.1235
    assert data["savings_pct"] == 12.35
    assert data["latency_ms"] == 1.24
    assert data["route_source"] == "ensemble"
    assert len(plan.decision_id) == 12


def test_turn_context_defaults_and_effective_message() -> None:
    ctx = _ctx()
    assert ctx.effective_message == "hello world"
    ctx2 = _ctx(raw_message="raw")
    assert ctx2.effective_message == "raw"
    assert ctx.max_iterations == 10
    assert ctx.mode == "act"


def test_with_metadata_is_non_destructive() -> None:
    ctx = _ctx(metadata={"a": 1})
    updated = ctx.with_metadata(b=2)
    assert updated.metadata == {"a": 1, "b": 2}
    assert ctx.metadata == {"a": 1}
    assert updated.message == ctx.message


def test_snapshot_with_and_without_route_plan() -> None:
    ctx = _ctx(message="x" * 500)
    snap = ctx.snapshot()
    assert snap["route_plan"] is None
    assert len(snap["message"]) == 200
    assert snap["metadata_keys"] == []

    ctx.route_plan = RoutePlan(target_tier="C3")
    snap2 = ctx.snapshot()
    assert snap2["route_plan"]["target_tier"] == "C3"


async def test_run_pipeline_happy_path() -> None:
    async def step_one(c: TurnContext) -> TurnContext:
        return c.with_metadata(one=True)

    async def step_two(c: TurnContext) -> TurnContext:
        return c.with_metadata(two=c.metadata.get("one"))

    final, results = await run_pipeline(_ctx(), [("one", step_one), ("two", step_two)])
    assert final.metadata == {"one": True, "two": True}
    assert [r.step_name for r in results] == ["one", "two"]
    assert all(r.success for r in results)
    assert all(r.warning is None and r.error is None for r in results)


async def test_run_pipeline_fail_open_keeps_going() -> None:
    async def boom(_c: TurnContext) -> TurnContext:
        raise ValueError("nope")

    async def after(c: TurnContext) -> TurnContext:
        return c.with_metadata(after=True)

    final, results = await run_pipeline(_ctx(), [("boom", boom), ("after", after)], fail_open=True)
    assert final.metadata == {"after": True}
    assert results[0].success is False
    assert results[0].error == "nope"
    assert results[0].warning is not None and "fail-open" in results[0].warning
    assert results[1].success is True


async def test_run_pipeline_fail_closed_raises_with_partial_ctx() -> None:
    async def boom(_c: TurnContext) -> TurnContext:
        raise RuntimeError("kaboom")

    with pytest.raises(EnginePipelineError) as excinfo:
        await run_pipeline(_ctx(), [("boom", boom)], fail_open=False)
    err = excinfo.value
    assert err.step_name == "boom"
    assert err.reason == "kaboom"
    assert err.partial_ctx is not None
    assert "boom" in str(err)


async def test_run_pipeline_timeout_is_reported() -> None:
    async def slow(_c: TurnContext) -> TurnContext:
        raise TimeoutError

    _final, results = await run_pipeline(_ctx(), [("slow", slow)], max_step_time=5.0)
    assert results[0].success is False
    assert "Step timeout after 5.0s" in (results[0].error or "")


async def test_run_pipeline_real_timeout_with_wait_for() -> None:
    async def sleeper(c: TurnContext) -> TurnContext:
        await asyncio.sleep(0.05)
        return c

    _final, results = await run_pipeline(_ctx(), [("sleeper", sleeper)], max_step_time=0.001)
    assert results[0].success is False
    assert "timeout" in (results[0].error or "").lower()


async def test_run_pipeline_fail_closed_timeout_raises() -> None:
    async def sleeper(c: TurnContext) -> TurnContext:
        await asyncio.sleep(0.05)
        return c

    with pytest.raises(EnginePipelineError):
        await run_pipeline(_ctx(), [("sleeper", sleeper)], fail_open=False, max_step_time=0.001)


def test_build_pipeline_event_summarizes() -> None:
    results = [
        StepResult(step_name="a", success=True, duration_ms=1.0),
        StepResult(step_name="b", success=False, duration_ms=2.0, error="bad"),
    ]
    event = build_pipeline_event(results)
    assert event.type is AgentEventType.PIPELINE_COMPLETE
    assert event.data["total_steps"] == 2
    assert event.data["failed_steps"] == 1
    assert event.data["steps"][1]["error"] == "bad"


def test_tooldef_fallback_is_defined() -> None:
    # app.models does not export ToolDef, so the fallback class is always used.
    td = pipeline_mod.ToolDef()
    assert td.name == ""
    assert td.description == ""
    assert td.parameters is None
