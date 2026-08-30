"""Time-travel and fork behavior for the Pregel engine."""

from __future__ import annotations

import pytest

from app.core.engine.pregel import (
    Checkpoint,
    CheckpointConfig,
    InMemoryCheckpointSaver,
    SqliteCheckpointSaver,
    StateGraph,
)


def _build_graph(checkpointer: InMemoryCheckpointSaver):
    graph = StateGraph()

    async def first(state):
        return {"count": state.get("count", 0) + 1}

    async def second(state):
        return {"count": state.get("count", 0) + 1}

    graph.add_node("first", first)
    graph.add_node("second", second)
    graph.add_edge("first", "second")
    graph.add_edge("second", "__end__")
    graph.set_entry_point("first")
    return graph.compile(checkpointer=checkpointer)


@pytest.mark.asyncio
async def test_get_state_and_invoke_from_specific_checkpoint():
    checkpointer = InMemoryCheckpointSaver()
    app = _build_graph(checkpointer)

    result = await app.invoke({"count": 0}, {"thread_id": "source"})
    assert result["count"] == 2
    history = await app.get_state_history({"thread_id": "source"})
    assert [checkpoint.step for checkpoint in history] == [2, 1]

    first_checkpoint = history[-1]
    state = await app.get_state({
        "thread_id": "source",
        "checkpoint_id": first_checkpoint.id,
    })
    assert state["count"] == 1

    resumed = await app.invoke({}, {
        "thread_id": "source",
        "checkpoint_id": first_checkpoint.id,
    })
    assert resumed["count"] == 2
    resumed_history = await app.get_state_history({"thread_id": "source"})
    assert resumed_history[0].parent_id == first_checkpoint.id


@pytest.mark.asyncio
async def test_missing_specific_checkpoint_raises():
    app = _build_graph(InMemoryCheckpointSaver())

    with pytest.raises(ValueError, match="Checkpoint not found"):
        await app.invoke({}, {
            "thread_id": "source",
            "checkpoint_id": "cp-missing",
        })


@pytest.mark.asyncio
async def test_specific_terminal_checkpoint_does_not_restart_graph():
    app = _build_graph(InMemoryCheckpointSaver())
    await app.invoke({"count": 0}, {"thread_id": "source"})
    terminal = (await app.get_state_history({"thread_id": "source"}))[0]

    result = await app.invoke({}, {
        "thread_id": "source",
        "checkpoint_id": terminal.id,
    })

    assert result["count"] == 2


@pytest.mark.asyncio
async def test_fork_continues_in_new_thread_without_mutating_source():
    checkpointer = InMemoryCheckpointSaver()
    app = _build_graph(checkpointer)
    await app.invoke({"count": 0, "branch": "source"}, {"thread_id": "source"})
    source_history = await app.get_state_history({"thread_id": "source"})
    source_first = source_history[-1]

    forked = await app.fork(
        {"thread_id": "source", "checkpoint_id": source_first.id},
        new_thread_id="experiment",
        values={"branch": "fork"},
    )

    assert forked["count"] == 2
    assert forked["branch"] == "fork"
    source_state = await app.get_state({"thread_id": "source"})
    assert source_state["branch"] == "source"

    fork_history = await app.get_state_history({"thread_id": "experiment"})
    assert len(fork_history) == 2
    assert fork_history[-1].parent_id == source_first.id
    assert fork_history[0].parent_id == fork_history[-1].id


@pytest.mark.asyncio
async def test_update_historical_state_preserves_selected_checkpoint_lineage():
    app = _build_graph(InMemoryCheckpointSaver())
    await app.invoke({"count": 0, "branch": "source"}, {"thread_id": "source"})
    source_first = (await app.get_state_history({"thread_id": "source"}))[-1]

    updated_config = await app.update_state(
        {"thread_id": "source", "checkpoint_id": source_first.id},
        {"branch": "edited"},
    )
    updated_checkpoint = (await app.get_state_history({"thread_id": "source"}))[0]

    assert updated_config["checkpoint_id"] == updated_checkpoint.id
    assert updated_checkpoint.parent_id == source_first.id
    assert updated_checkpoint.step == source_first.step
    assert updated_checkpoint.next_nodes == source_first.next_nodes


@pytest.mark.asyncio
async def test_checkpoint_id_is_scoped_to_thread():
    checkpointer = InMemoryCheckpointSaver()
    app = _build_graph(checkpointer)
    await app.invoke({"count": 0}, {"thread_id": "source"})
    checkpoint = (await app.get_state_history({"thread_id": "source"}))[-1]

    with pytest.raises(ValueError, match="Checkpoint not found"):
        await app.invoke({}, {
            "thread_id": "other",
            "checkpoint_id": checkpoint.id,
        })


@pytest.mark.asyncio
async def test_history_before_uses_write_order_instead_of_checkpoint_id_order():
    checkpointer = InMemoryCheckpointSaver()
    config = CheckpointConfig(thread_id="source")
    older = Checkpoint(id="cp-z-older", values={"count": 1}, step=1)
    newer = Checkpoint(id="cp-a-newer", values={"count": 2}, step=2, parent_id=older.id)
    await checkpointer.put(config, older)
    await checkpointer.put(config, newer)
    app = _build_graph(checkpointer)

    history = await app.get_state_history(
        {"thread_id": "source"},
        before=newer.id,
    )

    assert [checkpoint.id for checkpoint in history] == [older.id]


@pytest.mark.asyncio
async def test_sqlite_history_and_checkpoint_lookup_are_thread_scoped(tmp_path):
    checkpointer = SqliteCheckpointSaver(str(tmp_path / "pregel.db"))
    config = CheckpointConfig(thread_id="source")
    older = Checkpoint(id="cp-z-older", values={"count": 1}, step=1)
    newer = Checkpoint(id="cp-a-newer", values={"count": 2}, step=2, parent_id=older.id)
    await checkpointer.put(config, older)
    await checkpointer.put(config, newer)

    history = await checkpointer.list(config, before=newer.id)
    cross_thread = await checkpointer.get(CheckpointConfig(
        thread_id="other",
        checkpoint_id=older.id,
    ))

    assert [checkpoint.id for checkpoint in history] == [older.id]
    assert cross_thread is None
