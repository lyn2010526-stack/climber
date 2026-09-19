"""Tests for terminal sentinel (__end__/END) handling in the pregel engine."""

import asyncio

from app.core.engine.pregel.engine import ExecutionContext, PregelEngine
from app.core.engine.pregel.graph import StateGraph
from app.core.engine.pregel.state import GraphState


def build_conditional_entry(router):
    graph = StateGraph()
    graph.add_node("work", lambda state: {"ran": True})
    graph.set_conditional_entry_point(router)
    graph.add_edge("work", "__end__")
    return graph.compile()


async def test_conditional_entry_returning_end_completes_cleanly():
    calls = []

    def router(state):
        calls.append("router")
        return "__end__"

    result = await build_conditional_entry(router).invoke({}, {"thread_id": "end-entry"})

    assert calls == ["router"]
    assert result.get("ran") is None


async def test_conditional_entry_returning_uppercase_end_is_ignored():
    result = await build_conditional_entry(lambda state: "END").invoke({}, {"thread_id": "END-entry"})

    assert result.get("ran") is None


async def test_conditional_entry_normal_path_still_executes():
    def router(state):
        return "work"

    result = await build_conditional_entry(router).invoke({}, {"thread_id": "normal-entry"})

    assert result["ran"] is True


async def test_router_exception_ends_path_without_crash():
    def router(state):
        raise RuntimeError("boom")

    result = await build_conditional_entry(router).invoke({}, {"thread_id": "router-error"})

    assert result.get("ran") is None


async def test_mid_graph_conditional_returning_end_terminates_branch():
    calls = []

    def decide(state):
        calls.append("decide")
        return "__end__"

    graph = StateGraph()
    graph.add_node("start", lambda state: {"started": True})
    graph.add_node("work", lambda state: {"ran": True})
    graph.set_entry_point("start")
    graph.add_conditional_edges("start", decide)
    graph.add_edge("work", "__end__")

    result = await graph.compile().invoke({}, {"thread_id": "mid-end"})

    assert calls == ["decide"]
    assert result["started"] is True
    assert result.get("ran") is None


async def test_resume_nodes_mixing_terminal_and_real_drops_terminal():
    calls = []

    def work(state):
        calls.append("work")
        return {"resumed": True}

    graph = StateGraph()
    graph.add_node("work", work)
    graph.set_entry_point("work")
    graph.add_edge("work", "__end__")

    result = await graph.compile().invoke(
        {}, {"thread_id": "resume-mixed", "__resume_nodes__": ["__end__", "work"]}
    )

    assert calls == ["work"]
    assert result["resumed"] is True


async def test_astream_and_events_with_end_entry_do_not_crash():
    compiled = build_conditional_entry(lambda state: "__end__")

    steps = [step async for step in compiled.astream({}, {"thread_id": "astream-end"})]
    events = [event async for event in compiled.astream_events({}, {"thread_id": "events-end"})]

    assert steps
    assert events


async def test_execute_node_defends_against_terminal_sentinels():
    graph = StateGraph()
    graph.add_node("work", lambda state: {"ran": True})
    graph.set_entry_point("work")
    graph.add_edge("work", "__end__")
    engine = PregelEngine(graph)

    for sentinel in ("__end__", "END"):
        result = await engine._execute_node(sentinel, GraphState(), {}, ExecutionContext(thread_id="x"))
        assert result is None


async def test_start_router_awaitable_returning_end_is_filtered():
    async def router(state):
        await asyncio.sleep(0)
        return "__end__"

    result = await build_conditional_entry(router).invoke({}, {"thread_id": "async-end"})

    assert result.get("ran") is None
