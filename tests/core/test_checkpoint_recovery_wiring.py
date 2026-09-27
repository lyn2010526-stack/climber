"""Checkpoint recovery wiring tests (research-100 P1c follow-up).

Proves the engine-written checkpoint is reachable by the recovery path, that
absence stays structured, and that defaults are unchanged.
"""

from __future__ import annotations

from app.core.agent_engine import AgentEngine
from app.core.checkpoint import CheckpointData, InMemoryCheckpointStore, SQLiteCheckpointStore
from app.core.recovery import RecoveryManager


async def test_engine_written_checkpoint_is_recoverable_via_engine_store() -> None:
    engine = AgentEngine(model_registry=object(), tool_registry=object())
    store = engine.checkpoint_store

    session = engine.create_session(
        agent_id="", user_id="u", provider="openai", model_id="gpt-4o-mini",
        api_key="", session_id="s-rec", tools=[],
    )
    cp = CheckpointData(
        session_id="s-rec",
        messages=[{"role": "user", "content": "hi"}],
        iteration=1,
        status="processing",
    )
    await engine._save_checkpoint(session, cp, "s-rec-1")

    manager = RecoveryManager(store)
    recovered = await manager.recover_session("s-rec")
    assert recovered is not None
    assert recovered["iteration"] == 1
    assert recovered["checkpoint_id"] == "s-rec-1"
    assert recovered["interrupted"] is True  # "processing" with no final keys
    assert await manager.restore_session(session) is True
    assert session.messages[-1]["content"] == "hi"


async def test_recovery_absence_is_structured() -> None:
    manager = RecoveryManager(InMemoryCheckpointStore())
    assert await manager.recover_session("missing") is None

    class _Session:
        session_id = "missing"

    assert await manager.restore_session(_Session()) is False


def test_defaults_preserved() -> None:
    # Both the engine and the recovery manager now default to the persistent
    # store: an in-memory default meant a restart discarded every checkpoint.
    engine = AgentEngine(model_registry=object(), tool_registry=object())
    assert isinstance(engine.checkpoint_store, SQLiteCheckpointStore)
    assert isinstance(RecoveryManager()._store, SQLiteCheckpointStore)


async def test_thread_id_round_trips_through_inmemory_store() -> None:
    engine = AgentEngine(model_registry=object(), tool_registry=object())
    session = engine.create_session(
        agent_id="", user_id="u", provider="openai", model_id="gpt-4o-mini",
        api_key="", session_id="s-turn", tools=[],
    )
    session.current_turn_id = "turn-42"
    cp = CheckpointData(session_id="s-turn", messages=[], iteration=1, status="processing")
    await engine._save_checkpoint(session, cp, "s-turn-1")

    manager = RecoveryManager(engine.checkpoint_store)
    recovered = await manager.recover_session("s-turn")
    assert recovered is not None
    assert recovered["turn_id"] == "turn-42"
