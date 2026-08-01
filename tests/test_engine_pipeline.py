"""Tests for pipeline execution engine."""

import pytest

from app.core.engine.pipeline import (
    PipelineError,
    RoutePlan,
    StepResult,
    TurnContext,
    TurnStep,
    build_pipeline_event,
    run_pipeline,
)


@pytest.fixture
def base_context() -> TurnContext:
    return TurnContext(
        message="Hello world",
        session_id="test-session",
        model="gpt-4o",
        provider="openai",
        api_key="test-key",
        system_prompt="You are a test assistant",
    )


class TestTurnContext:
    def test_creation(self, base_context: TurnContext) -> None:
        assert base_context.message == "Hello world"
        assert base_context.session_id == "test-session"
        assert base_context.metadata == {}

    def test_with_metadata(self, base_context: TurnContext) -> None:
        ctx2 = base_context.with_metadata(routed=True, tier="C1")
        assert ctx2.metadata["routed"] is True
        assert ctx2.metadata["tier"] == "C1"
        # Original unchanged
        assert base_context.metadata == {}

    def test_effective_message(self, base_context: TurnContext) -> None:
        assert base_context.effective_message == "Hello world"
        ctx2 = TurnContext(
            message="processed",
            session_id="s",
            model="m",
            provider="p",
            api_key="k",
            raw_message="original user input",
        )
        assert ctx2.effective_message == "original user input"

    def test_snapshot(self, base_context: TurnContext) -> None:
        snap = base_context.snapshot()
        assert snap["session_id"] == "test-session"
        assert snap["model"] == "gpt-4o"


class TestRoutePlan:
    def test_to_dict(self) -> None:
        plan = RoutePlan(
            target_tier="C2",
            model="gpt-4o",
            provider="openai",
            confidence=0.85,
            probabilities={"C1": 0.1, "C2": 0.85, "C3": 0.05},
            savings_pct=70.0,
        )
        d = plan.to_dict()
        assert d["target_tier"] == "C2"
        assert d["confidence"] == 0.85
        assert d["decision_id"] is not None


class TestRunPipeline:
    @pytest.mark.asyncio
    async def test_single_step(self, base_context: TurnContext) -> None:
        async def step(ctx: TurnContext) -> TurnContext:
            return ctx.with_metadata(step1_done=True)

        ctx, results = await run_pipeline(base_context, [("test_step", step)])
        assert len(results) == 1
        assert results[0].success is True
        assert ctx.metadata["step1_done"] is True

    @pytest.mark.asyncio
    async def test_multiple_steps(self, base_context: TurnContext) -> None:
        async def step1(ctx: TurnContext) -> TurnContext:
            return ctx.with_metadata(count=1)

        async def step2(ctx: TurnContext) -> TurnContext:
            return ctx.with_metadata(count=ctx.metadata.get("count", 0) + 1)

        ctx, results = await run_pipeline(
            base_context,
            [("s1", step1), ("s2", step2)],
        )
        assert len(results) == 2
        assert all(r.success for r in results)
        assert ctx.metadata["count"] == 2

    @pytest.mark.asyncio
    async def test_fail_open(self, base_context: TurnContext) -> None:
        async def bad_step(ctx: TurnContext) -> TurnContext:
            raise RuntimeError("step failed")

        async def good_step(ctx: TurnContext) -> TurnContext:
            return ctx.with_metadata(recovered=True)

        ctx, results = await run_pipeline(
            base_context,
            [("bad", bad_step), ("good", good_step)],
            fail_open=True,
        )
        assert results[0].success is False
        assert results[1].success is True
        assert ctx.metadata["recovered"] is True

    @pytest.mark.asyncio
    async def test_fail_closed(self, base_context: TurnContext) -> None:
        async def bad_step(ctx: TurnContext) -> TurnContext:
            raise RuntimeError("critical failure")

        with pytest.raises(PipelineError) as exc_info:
            await run_pipeline(base_context, [("bad", bad_step)], fail_open=False)
        assert exc_info.value.step_name == "bad"

    @pytest.mark.asyncio
    async def test_step_timing(self, base_context: TurnContext) -> None:
        async def slow_step(ctx: TurnContext) -> TurnContext:
            import asyncio
            await asyncio.sleep(0.01)
            return ctx

        ctx, results = await run_pipeline(base_context, [("slow", slow_step)])
        assert results[0].duration_ms >= 10


class TestBuildPipelineEvent:
    def test_event_structure(self) -> None:
        results = [
            StepResult(step_name="s1", success=True, duration_ms=5.0),
            StepResult(step_name="s2", success=False, duration_ms=10.0, error="failed"),
        ]
        event = build_pipeline_event(results)
        assert event.data["total_steps"] == 2
        assert event.data["failed_steps"] == 1
        assert event.data["steps"][0]["name"] == "s1"
