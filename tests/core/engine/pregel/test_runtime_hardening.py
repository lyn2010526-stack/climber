import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.core.engine.pregel.checkpoint import (
    Checkpoint,
    CheckpointConfig,
    InMemoryCheckpointSaver,
    SqliteCheckpointSaver,
)
from app.core.engine.pregel.engine import PregelEngine
from app.core.engine.pregel.graph import StateGraph
from app.core.engine.pregel.policies import RetryPolicy, TimeoutPolicy
from app.core.engine.pregel.state import GraphState
from app.core.engine.pregel.streaming import StreamEvent, StreamEventType, StreamManager


def build_linear_graph(first, second=None):
    graph = StateGraph()
    graph.add_node("first", first)
    graph.set_entry_point("first")
    if second is None:
        graph.add_edge("first", "__end__")
    else:
        graph.add_node("second", second)
        graph.add_edge("first", "second")
        graph.add_edge("second", "__end__")
    return graph


@pytest.mark.asyncio
async def test_compiled_graph_concurrent_invocations_are_isolated():
    saver = InMemoryCheckpointSaver()

    async def first(state):
        await asyncio.sleep(0.02 if state["value"] == "slow" else 0)
        return {"first": state["value"]}

    async def second(state):
        return {"result": state["first"]}

    compiled = build_linear_graph(first, second).compile(checkpointer=saver)
    slow, fast = await asyncio.gather(
        compiled.invoke({"value": "slow"}, {"thread_id": "slow-thread"}),
        compiled.invoke({"value": "fast"}, {"thread_id": "fast-thread"}),
    )

    assert slow["result"] == "slow"
    assert fast["result"] == "fast"
    assert (await saver.get(CheckpointConfig("slow-thread"))).values["result"] == "slow"
    assert (await saver.get(CheckpointConfig("fast-thread"))).values["result"] == "fast"


@pytest.mark.asyncio
async def test_missing_thread_id_creates_independent_threads():
    saver = InMemoryCheckpointSaver()
    compiled = build_linear_graph(lambda state: {"value": state["value"]}).compile(
        checkpointer=saver
    )

    await compiled.invoke({"value": 1})
    await compiled.invoke({"value": 2})

    assert len(saver._thread_index) == 2
    assert "default" not in saver._thread_index


@pytest.mark.asyncio
async def test_interrupt_before_resumes_by_executing_interrupted_node():
    saver = InMemoryCheckpointSaver()
    calls = []

    def first(state):
        calls.append("first")
        return {"first_ran": True}

    compiled = build_linear_graph(first).compile(
        checkpointer=saver, interrupt_before=["first"]
    )
    config = {"thread_id": "before"}

    interrupted = await compiled.invoke({}, config)
    checkpoint = await saver.get(CheckpointConfig("before"))

    assert interrupted["__interrupted__"] is True
    assert checkpoint.next_nodes == ["first"]
    assert calls == []

    resumed = await compiled.resume_with(config, "approved")

    assert resumed["first_ran"] is True
    assert calls == ["first"]


@pytest.mark.asyncio
async def test_interrupt_after_merges_update_and_resumes_at_successor():
    saver = InMemoryCheckpointSaver()
    calls = []

    def first(state):
        calls.append("first")
        return {"count": 1}

    def second(state):
        calls.append("second")
        return {"count_seen": state["count"]}

    compiled = build_linear_graph(first, second).compile(
        checkpointer=saver, interrupt_after=["first"]
    )
    config = {"thread_id": "after"}

    interrupted = await compiled.invoke({}, config)
    checkpoint = await saver.get(CheckpointConfig("after"))

    assert interrupted["count"] == 1
    assert checkpoint.next_nodes == ["second"]
    assert calls == ["first"]

    resumed = await compiled.resume_with(config, "approved")

    assert resumed["count_seen"] == 1
    assert calls == ["first", "second"]


@pytest.mark.asyncio
async def test_node_timeout_reaches_error_handler_and_error_event():
    async def slow_node(state):
        await asyncio.sleep(0.05)
        return {"finished": True}

    graph = build_linear_graph(slow_node)
    engine = PregelEngine(
        graph,
        retry_policy=RetryPolicy(max_attempts=1),
        timeout_policy=TimeoutPolicy(node_timeout=0.005),
    )

    events = [
        event
        async for event in engine.astream_events(
            GraphState(), {"thread_id": "node-timeout"}
        )
    ]

    error_events = [event for event in events if event.type == StreamEventType.ERROR]
    assert len(error_events) == 1
    assert error_events[0].node == "first"
    assert error_events[0].data["error_type"] == "TimeoutError"
    assert any(event.type == StreamEventType.CHECKPOINT for event in events)


@pytest.mark.asyncio
async def test_run_timeout_reaches_error_handler():
    async def slow_node(state):
        await asyncio.sleep(0.05)
        return {"finished": True}

    engine = PregelEngine(
        build_linear_graph(slow_node),
        retry_policy=RetryPolicy(max_attempts=1),
        timeout_policy=TimeoutPolicy(run_timeout=0.005),
    )

    result = await engine.run(GraphState(), {"thread_id": "run-timeout"})

    assert result["__error__"] is True
    assert result["error_node"] == "__run__"


@pytest.mark.asyncio
async def test_stream_manager_broadcasts_to_every_subscriber():
    manager = StreamManager()
    event = StreamEvent(type=StreamEventType.CHECKPOINT, data={"id": "cp"})

    async def receive_one():
        async for received in manager.subscribe():
            return received

    subscribers = [asyncio.create_task(receive_one()) for _ in range(2)]
    await asyncio.sleep(0)
    await manager.emit(event)

    assert await asyncio.gather(*subscribers) == [event, event]


@pytest.mark.asyncio
async def test_checkpoint_pagination_uses_step_and_creation_time():
    saver = InMemoryCheckpointSaver()
    config = CheckpointConfig("pagination")
    now = datetime.now(UTC)
    older = Checkpoint(id="cp-older", step=2, created_at=now - timedelta(seconds=1))
    newer = Checkpoint(id="cp-newer", step=2, created_at=now)
    first = Checkpoint(id="cp-first", step=1, created_at=now + timedelta(seconds=1))
    for checkpoint in (older, newer, first):
        await saver.put(config, checkpoint)

    page = await saver.list(config, limit=2)
    next_page = await saver.list(config, before=page[-1].id)

    assert [checkpoint.id for checkpoint in page] == ["cp-newer", "cp-older"]
    assert [checkpoint.id for checkpoint in next_page] == ["cp-first"]


@pytest.mark.asyncio
async def test_sqlite_checkpoint_pagination_uses_same_cursor_order(tmp_path):
    saver = SqliteCheckpointSaver(str(tmp_path / "checkpoints.db"))
    config = CheckpointConfig("pagination")
    now = datetime.now(UTC)
    checkpoints = [
        Checkpoint(id="cp-older", step=2, created_at=now - timedelta(seconds=1)),
        Checkpoint(id="cp-newer", step=2, created_at=now),
        Checkpoint(id="cp-first", step=1, created_at=now + timedelta(seconds=1)),
    ]
    for checkpoint in checkpoints:
        await saver.put(config, checkpoint)

    page = await saver.list(config, limit=2)
    next_page = await saver.list(config, before=page[-1].id)

    assert [checkpoint.id for checkpoint in page] == ["cp-newer", "cp-older"]
    assert [checkpoint.id for checkpoint in next_page] == ["cp-first"]
