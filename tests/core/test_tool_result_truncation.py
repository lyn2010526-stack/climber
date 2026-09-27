"""Tool result truncation and bounded tool concurrency tests.

Concurrency design references:

* https://docs.python.org/3/library/asyncio-task.html#task-groups
* https://anyio.readthedocs.io/en/stable/synchronization.html#capacity-limiters
* https://docs.langchain.com/oss/python/langgraph/use-graph-api#map-reduce-and-the-send-api
* https://docs.ray.io/en/latest/ray-core/actors/async_api.html#setting-concurrency-in-async-actors

Anthropic's guidance on agent tool design caps tool responses because the
context window degrades as it fills (context rot):

    "For Claude Code, we restrict tool responses to 25,000 tokens by default.
     We suggest implementing some combination of pagination, range selection,
     filtering, and/or truncation with sensible default parameter values for
     any tool responses that could use up lots of context."
    -- https://www.anthropic.com/engineering/writing-tools-for-agents

Their own concise/detailed measurement shows a single Slack tool returning
206 tokens detailed vs 72 concise, so unbounded tool output is the dominant
avoidable consumer of an agent's context.

`ParallelToolExecutor._execute_one` (app/core/parallel.py) is the single point
every one of the 49 registered tools flows through before the result reaches
the model, so truncation belongs there. These tests pin that contract: a
truncation notice is appended rather than replacing content, the model is
told how to get the rest, short results pass through byte-identical, and the
boundary is configurable.
"""

from __future__ import annotations

import asyncio

from app.core.parallel import ParallelToolExecutor


class _Registry:
    """Minimal registry: returns whatever payload the test hands it."""

    def __init__(self, payload: str) -> None:
        self._payload = payload
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, name: str, arguments: dict):
        self.calls.append((name, arguments))
        return self._payload


class _ConcurrencyRegistry:
    def __init__(self, release: asyncio.Event, fail_name: str | None = None) -> None:
        self.release = release
        self.fail_name = fail_name
        self.running = 0
        self.peak = 0
        self.peak_reached = asyncio.Event()
        self.started = asyncio.Event()

    async def execute(self, name: str, arguments: dict):
        self.running += 1
        self.started.set()
        self.peak = max(self.peak, self.running)
        if self.peak >= 2:
            self.peak_reached.set()
        try:
            if name == self.fail_name:
                raise RuntimeError("partial failure")
            await self.release.wait()
            return name
        finally:
            self.running -= 1


def _run(registry: _Registry, limit: int | None) -> str:
    async def go() -> str:
        ex = ParallelToolExecutor(registry, timeout_per_tool=5.0, max_result_chars=limit)
        results = await ex.execute_all(
            [{"id": "c1", "function": {"name": "read_file", "arguments": {}}}]
        )
        return results[0].result

    return asyncio.run(go())


def test_short_result_passes_through_unchanged() -> None:
    payload = "a normal sized tool result"
    assert _run(_Registry(payload), limit=10_000) == payload


def test_oversized_result_is_truncated() -> None:
    payload = "x" * 50_000
    out = _run(_Registry(payload), limit=1_000)
    assert len(out) < len(payload)
    assert "x" * 500 in out


def test_truncation_notice_tells_model_how_to_recover() -> None:
    """A silent truncation loses information the model cannot recover.

    Anthropic pairs truncation with guidance to steer the agent toward
    cheaper access patterns, so the notice must name the fix.
    """
    out = _run(_Registry("y" * 50_000), limit=1_000)
    assert "truncated" in out.lower()
    assert "chars" in out.lower() or "character" in out.lower()


def test_truncation_reports_original_size() -> None:
    out = _run(_Registry("z" * 12_345), limit=1_000)
    assert "12345" in out.replace(",", "")


def test_limit_is_configurable() -> None:
    """A tighter limit must cut earlier; the cap is not hardcoded."""
    payload = "q" * 5_000
    loose = _run(_Registry(payload), limit=4_000)
    tight = _run(_Registry(payload), limit=500)
    assert len(tight) < len(loose)


def test_truncation_preserves_the_head() -> None:
    """Keep the beginning: that is where the summary and identifiers live."""
    payload = "HEADMARKER" + "f" * 20_000
    out = _run(_Registry(payload), limit=1_000)
    assert out.startswith("HEADMARKER")


def test_default_limit_is_bounded() -> None:
    """The default must exist and be finite, otherwise nothing is capped."""
    ex = ParallelToolExecutor(_Registry("short"), timeout_per_tool=1.0)
    assert ex.max_result_chars is not None
    assert 0 < ex.max_result_chars <= 200_000


def test_truncation_does_not_break_success_flag() -> None:
    """Truncated is still a successful call; the model must not retry it."""
    async def go() -> bool:
        ex = ParallelToolExecutor(_Registry("w" * 40_000), timeout_per_tool=5.0, max_result_chars=1_000)
        results = await ex.execute_all(
            [{"id": "c1", "function": {"name": "read_file", "arguments": {}}}]
        )
        return results[0].success and results[0].error == ""

    assert asyncio.run(go()) is True


def test_error_messages_are_not_truncated() -> None:
    """An error that gets cut mid-sentence is worse than a long error.

    Errors are also the model's only recovery signal, so the cap applies to
    results only.
    """
    async def go() -> str:
        class _Failing:
            async def execute(self, name, arguments):
                raise ValueError("detail " * 2000)

        ex = ParallelToolExecutor(_Failing(), timeout_per_tool=5.0, max_result_chars=100)
        results = await ex.execute_all(
            [{"id": "c1", "function": {"name": "read_file", "arguments": {}}}]
        )
        return results[0].error

    err = asyncio.run(go())
    assert err.startswith("detail detail")
    assert "truncated" not in err.lower()


def test_debug_recovery_output_is_also_capped() -> None:
    """_handle_tool_debug re-injects recovered output through a second path.

    AgentEngine._handle_tool_debug assigns debug_loop output straight onto
    ToolExecutionResult.result, bypassing the executor, so it needs the same
    cap or a long recovered payload reintroduces the overflow.
    """
    from app.core.agent_engine import AgentEngine

    engine = AgentEngine.__new__(AgentEngine)
    engine._tool_result_char_limit = 500

    class _Result:
        def __init__(self) -> None:
            self.tool_name = "read_file"
            self.error = "boom"
            self.result = ""
            self.success = False
            self.arguments: dict = {}

    class _Fixed:
        success = True
        output = "R" * 30_000

    async def go() -> str:
        from app.core.session import AgentSession

        engine.debug_loop = type(
            "_Loop",
            (),
            {"recover": staticmethod(lambda **kw: _async(_Fixed()))},
        )()
        session = AgentSession(session_id="s1", agent_id="a1", user_id="u1")
        tr = _Result()
        await engine._handle_tool_debug(session, tr)
        return tr.result

    async def _async(value):
        return value

    out = asyncio.run(go())
    assert len(out) < 30_000
    assert "truncated" in out.lower()


def test_parallel_execution_is_bounded_and_preserves_partial_failures() -> None:
    async def go() -> tuple[int, list[bool]]:
        release = asyncio.Event()
        registry = _ConcurrencyRegistry(release, fail_name="fail")
        ex = ParallelToolExecutor(
            registry,
            timeout_per_tool=5.0,
            max_concurrency=2,
        )
        calls = [
            {"id": str(i), "function": {"name": name, "arguments": {}}}
            for i, name in enumerate(("a", "b", "fail", "c"))
        ]
        task = asyncio.create_task(ex.execute_all(calls))
        await registry.peak_reached.wait()
        release.set()
        results = await task
        return registry.peak, [result.success for result in results]

    peak, successes = asyncio.run(go())
    assert peak == 2
    assert successes == [True, True, False, True]


def test_parallel_cancellation_propagates_and_releases_capacity() -> None:
    async def go() -> tuple[bool, int]:
        release = asyncio.Event()
        registry = _ConcurrencyRegistry(release)
        ex = ParallelToolExecutor(registry, timeout_per_tool=5.0, max_concurrency=1)
        task = asyncio.create_task(
            ex.execute_all(
                [
                    {"id": "a", "function": {"name": "a", "arguments": {}}},
                    {"id": "b", "function": {"name": "b", "arguments": {}}},
                ]
            )
        )
        await registry.started.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return True, registry.running
        return False, registry.running

    cancelled, running = asyncio.run(go())
    assert cancelled is True
    assert running == 0
