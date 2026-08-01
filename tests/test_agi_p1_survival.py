"""Tests for AGI P1 Survival Layer.

Covers SQLiteCheckpointStore CRUD, turn lifecycle persistence,
task pause/resume/terminate/restart, checkpoint recovery, and auto-recovery.
"""

from __future__ import annotations

import os

os.environ["APP_TESTING"] = "true"

import pytest
import pytest_asyncio

from app.core.agent_engine import AgentEngine, AgentSession
from app.core.checkpoint import CheckpointData, SQLiteCheckpointStore
from app.core.recovery import RecoveryManager
from app.core.task_state_machine import TaskState
from app.models.registry import ModelRegistry
from app.storage import init_db, engine, Base
from app.storage.database import CheckpointRecord, Turn
from app.storage.repository import SessionRepository, TurnRepository
from app.tools import ToolRegistry


@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(init_db())
    finally:
        loop.close()
    yield


@pytest.fixture(autouse=True)
def cleanup_db():
    yield
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async def _cleanup():
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
                await init_db()
            loop.run_until_complete(_cleanup())
        finally:
            loop.close()
    except Exception:
        pass


@pytest_asyncio.fixture
async def checkpoint_store():
    return SQLiteCheckpointStore()


@pytest_asyncio.fixture
async def turn_repository():
    return TurnRepository()


@pytest_asyncio.fixture
async def recovery_manager(checkpoint_store):
    return RecoveryManager(checkpoint_store=checkpoint_store)


@pytest_asyncio.fixture
async def engine_with_registries():
    model_registry = ModelRegistry()
    tool_registry = ToolRegistry()

    @tool_registry.tool(name="echo", description="Echo back the input")
    async def echo(text: str) -> str:
        return f"Echo: {text}"

    engine = AgentEngine(
        model_registry=model_registry,
        tool_registry=tool_registry,
    )
    return engine


# --- SQLiteCheckpointStore CRUD Tests ---

@pytest.mark.asyncio
async def test_checkpoint_save_creates_record(checkpoint_store):
    cp = CheckpointData(
        session_id="sess-1",
        messages=[{"role": "user", "content": "hello"}],
        iteration=1,
        status="processing",
    )
    cid = await checkpoint_store.save(None, cp, checkpoint_id="cp-test-1")
    assert cid == "cp-test-1"

    loaded = await checkpoint_store.get(None, "cp-test-1")
    assert loaded is not None
    assert loaded.session_id == "sess-1"
    assert loaded.iteration == 1
    assert loaded.status == "processing"


@pytest.mark.asyncio
async def test_checkpoint_save_upsert(checkpoint_store):
    cp = CheckpointData(
        session_id="sess-2",
        messages=[{"role": "user", "content": "hello"}],
        iteration=1,
        status="processing",
    )
    await checkpoint_store.save(None, cp, checkpoint_id="cp-upsert-1")

    cp_updated = CheckpointData(
        session_id="sess-2",
        messages=[{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}],
        iteration=2,
        status="completed",
    )
    await checkpoint_store.save(None, cp_updated, checkpoint_id="cp-upsert-1")

    loaded = await checkpoint_store.get(None, "cp-upsert-1")
    assert loaded is not None
    assert loaded.iteration == 2
    assert loaded.status == "completed"
    assert len(loaded.messages) == 2


@pytest.mark.asyncio
async def test_checkpoint_load_by_session_and_turn(checkpoint_store):
    cp = CheckpointData(
        session_id="sess-3",
        messages=[{"role": "user", "content": "test"}],
        iteration=3,
        status="processing",
    )
    await checkpoint_store.save(None, cp, thread_id="turn-abc", checkpoint_id="cp-load-1")

    loaded = await checkpoint_store.load("sess-3", "turn-abc")
    assert loaded is not None
    assert loaded.session_id == "sess-3"
    assert loaded.iteration == 3


@pytest.mark.asyncio
async def test_checkpoint_list_for_session(checkpoint_store):
    for i in range(3):
        cp = CheckpointData(
            session_id="sess-list",
            messages=[{"role": "user", "content": f"msg-{i}"}],
            iteration=i,
            status="processing",
        )
        await checkpoint_store.save(None, cp, checkpoint_id=f"cp-list-{i}")

    ids = await checkpoint_store.list_for_session(None, "sess-list")
    assert len(ids) == 3

    full_list = await checkpoint_store.list("sess-list")
    assert len(full_list) == 3
    assert all(isinstance(c, CheckpointData) for c in full_list)


@pytest.mark.asyncio
async def test_checkpoint_delete_single(checkpoint_store):
    cp = CheckpointData(
        session_id="sess-del",
        messages=[],
        iteration=0,
        status="processing",
    )
    cid = await checkpoint_store.save(None, cp, checkpoint_id="cp-del-1")

    result = await checkpoint_store.delete(cid)
    assert result is True

    loaded = await checkpoint_store.get(None, cid)
    assert loaded is None


@pytest.mark.asyncio
async def test_checkpoint_delete_for_session(checkpoint_store):
    for i in range(2):
        cp = CheckpointData(
            session_id="sess-del-all",
            messages=[],
            iteration=i,
            status="processing",
        )
        await checkpoint_store.save(None, cp, checkpoint_id=f"cp-del-all-{i}")

    count = await checkpoint_store.delete_for_session(None, "sess-del-all")
    assert count == 2

    ids = await checkpoint_store.list_for_session(None, "sess-del-all")
    assert len(ids) == 0


@pytest.mark.asyncio
async def test_checkpoint_get_latest(checkpoint_store):
    for i in range(3):
        cp = CheckpointData(
            session_id="sess-latest",
            messages=[],
            iteration=i,
            status="processing",
        )
        await checkpoint_store.save(None, cp, checkpoint_id=f"cp-latest-{i}")

    result = await checkpoint_store.get_latest(None, "sess-latest")
    assert result is not None
    checkpoint, cid = result
    assert checkpoint.iteration == 2


# --- Turn Lifecycle Persistence Tests ---

async def _create_test_session(session_id: str) -> None:
    """Helper to create a session row so turn FK constraint passes."""
    from app.storage import async_session
    from app.storage.database import Session, Agent
    async with async_session() as db:
        agent = await db.execute(
            __import__("sqlalchemy").select(Agent).where(Agent.id == "test-agent")
        )
        if agent.scalar_one_or_none() is None:
            db.add(Agent(
                id="test-agent",
                user_id="test-user",
                name="Test Agent",
                provider="test",
                model_id="test-model",
                api_key_encrypted="",
            ))
        db.add(Session(
            id=session_id,
            agent_id="test-agent",
            user_id="test-user",
            status="pending",
        ))
        await db.commit()


@pytest.mark.asyncio
async def test_turn_start(turn_repository):
    await _create_test_session("sess-turn-1")
    turn = await turn_repository.start_turn(
        session_id="sess-turn-1",
        metadata_={"message": "hello"},
    )
    assert turn.id is not None
    assert turn.session_id == "sess-turn-1"
    assert turn.status == "running"
    assert turn.started_at is not None


@pytest.mark.asyncio
async def test_turn_complete(turn_repository):
    await _create_test_session("sess-turn-2")
    turn = await turn_repository.start_turn(session_id="sess-turn-2")
    completed = await turn_repository.complete_turn(
        turn_id=turn.id,
        result="Done!",
        iteration_count=5,
        tokens_used=1500,
    )
    assert completed is not None
    assert completed.status == "completed"
    assert completed.result == "Done!"
    assert completed.completed_at is not None
    assert completed.iteration_count == 5
    assert completed.tokens_used == 1500


@pytest.mark.asyncio
async def test_turn_fail(turn_repository):
    await _create_test_session("sess-turn-3")
    turn = await turn_repository.start_turn(session_id="sess-turn-3")
    failed = await turn_repository.fail_turn(
        turn_id=turn.id,
        error_message="Model timeout",
        iteration_count=2,
        tokens_used=500,
    )
    assert failed is not None
    assert failed.status == "failed"
    assert failed.error == "Model timeout"
    assert failed.error_message == "Model timeout"
    assert failed.iteration_count == 2
    assert failed.tokens_used == 500


@pytest.mark.asyncio
async def test_turn_list_by_session(turn_repository):
    await _create_test_session("sess-turn-list")
    for i in range(3):
        await turn_repository.start_turn(session_id="sess-turn-list")

    turns = await turn_repository.list_by_session("sess-turn-list")
    assert len(turns) == 3
    assert all(t.session_id == "sess-turn-list" for t in turns)


# --- Task Pause/Resume/Terminate/Restart Tests ---

@pytest.mark.asyncio
async def test_session_pause_and_resume():
    session = AgentSession(
        session_id="sess-pause",
        agent_id="agent-1",
        user_id="user-1",
        provider="openai",
        model_id="gpt-4",
        api_key="test-key",
    )
    await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")

    await session.pause()
    assert session.state_machine.state == TaskState.PAUSED
    assert session.paused_at is not None

    await session.resume()
    assert session.state_machine.state == TaskState.PROCESSING
    assert session.paused_at is None


@pytest.mark.asyncio
async def test_session_terminate():
    session = AgentSession(
        session_id="sess-term",
        agent_id="agent-1",
        user_id="user-1",
        provider="openai",
        model_id="gpt-4",
        api_key="test-key",
    )
    await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")

    await session.terminate(reason="user_cancelled")
    assert session.state_machine.state == TaskState.CANCELLED
    assert session.termination_reason == "user_cancelled"


@pytest.mark.asyncio
async def test_session_restart():
    session = AgentSession(
        session_id="sess-restart",
        agent_id="agent-1",
        user_id="user-1",
        provider="openai",
        model_id="gpt-4",
        api_key="test-key",
    )
    await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")
    await session.terminate(reason="test")

    await session.restart()
    assert session.state_machine.state == TaskState.PENDING
    assert session.restart_count == 1
    assert session.termination_reason is None


@pytest.mark.asyncio
async def test_session_restart_increments_count():
    session = AgentSession(
        session_id="sess-restart-multi",
        agent_id="agent-1",
        user_id="user-1",
        provider="openai",
        model_id="gpt-4",
        api_key="test-key",
    )

    for i in range(3):
        await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")
        await session.terminate(reason=f"test-{i}")
        await session.restart()

    assert session.restart_count == 3


@pytest.mark.asyncio
async def test_session_restart_from_failed():
    session = AgentSession(
        session_id="sess-restart-failed",
        agent_id="agent-1",
        user_id="user-1",
        provider="openai",
        model_id="gpt-4",
        api_key="test-key",
    )
    await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")
    await session.state_machine.transition(TaskState.FAILED, trigger="error")

    await session.restart()
    assert session.state_machine.state == TaskState.PENDING
    assert session.restart_count == 1


@pytest.mark.asyncio
async def test_session_restart_from_paused():
    session = AgentSession(
        session_id="sess-restart-paused",
        agent_id="agent-1",
        user_id="user-1",
        provider="openai",
        model_id="gpt-4",
        api_key="test-key",
    )
    await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")
    await session.pause()

    await session.restart()
    assert session.state_machine.state == TaskState.PENDING
    assert session.paused_at is None


# --- Checkpoint Recovery Tests ---

@pytest.mark.asyncio
async def test_recovery_recover_session(checkpoint_store, recovery_manager):
    cp = CheckpointData(
        session_id="sess-recover",
        messages=[{"role": "user", "content": "help"}],
        iteration=5,
        status="failed",
        channel_values={"last_tool_calls": ["search"]},
    )
    await checkpoint_store.save(None, cp, checkpoint_id="cp-recover-1")

    result = await recovery_manager.recover_session("sess-recover")
    assert result is not None
    assert result["session_id"] == "sess-recover"
    assert result["iteration"] == 5
    assert result["status"] == "failed"
    assert result["checkpoint_id"] == "cp-recover-1"


@pytest.mark.asyncio
async def test_recovery_no_checkpoint(recovery_manager):
    result = await recovery_manager.recover_session("sess-nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_recovery_list_recoverable_sessions(checkpoint_store, turn_repository, recovery_manager):
    await _create_test_session("sess-recoverable")
    cp = CheckpointData(
        session_id="sess-recoverable",
        messages=[],
        iteration=1,
        status="failed",
    )
    await checkpoint_store.save(None, cp, checkpoint_id="cp-recoverable-1")

    await turn_repository.start_turn(session_id="sess-recoverable")
    turn = await turn_repository.start_turn(session_id="sess-recoverable")
    await turn_repository.fail_turn(turn.id, "error")

    recoverable = await recovery_manager.list_recoverable_sessions()
    session_ids = [r["session_id"] for r in recoverable]
    assert "sess-recoverable" in session_ids


@pytest.mark.asyncio
async def test_recovery_auto_recover(checkpoint_store, turn_repository, recovery_manager):
    await _create_test_session("sess-autorecover")
    cp = CheckpointData(
        session_id="sess-autorecover",
        messages=[{"role": "user", "content": "test"}],
        iteration=2,
        status="failed",
    )
    await checkpoint_store.save(None, cp, checkpoint_id="cp-autorecover-1")

    turn = await turn_repository.start_turn(session_id="sess-autorecover")
    await turn_repository.fail_turn(turn.id, "timeout")

    results = await recovery_manager.auto_recover()
    recovered = [r for r in results if r["status"] == "recovered"]
    assert len(recovered) >= 1
    assert any(r["session_id"] == "sess-autorecover" for r in recovered)


# --- Integration: Session state transitions go through state machine ---

@pytest.mark.asyncio
async def test_pause_through_state_machine():
    session = AgentSession(
        session_id="sess-pause-sm",
        agent_id="agent-1",
        user_id="user-1",
        provider="openai",
        model_id="gpt-4",
        api_key="test-key",
    )
    await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")

    await session.pause()
    assert session.state_machine.state == TaskState.PAUSED
    assert session.state_machine.metadata.get("transition_trigger") == "user_pause"


@pytest.mark.asyncio
async def test_resume_through_state_machine():
    session = AgentSession(
        session_id="sess-resume-sm",
        agent_id="agent-1",
        user_id="user-1",
        provider="openai",
        model_id="gpt-4",
        api_key="test-key",
    )
    await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")
    await session.pause()

    await session.resume()
    assert session.state_machine.state == TaskState.PROCESSING
    assert session.state_machine.metadata.get("transition_trigger") == "user_resume"


@pytest.mark.asyncio
async def test_terminate_through_state_machine():
    session = AgentSession(
        session_id="sess-term-sm",
        agent_id="agent-1",
        user_id="user-1",
        provider="openai",
        model_id="gpt-4",
        api_key="test-key",
    )
    await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")

    await session.terminate(reason="user_abort")
    assert session.state_machine.state == TaskState.CANCELLED
    assert session.state_machine.metadata.get("transition_trigger") == "user_abort"


@pytest.mark.asyncio
async def test_restart_through_state_machine():
    session = AgentSession(
        session_id="sess-restart-sm",
        agent_id="agent-1",
        user_id="user-1",
        provider="openai",
        model_id="gpt-4",
        api_key="test-key",
    )
    await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")
    await session.state_machine.transition(TaskState.FAILED, trigger="error")

    await session.restart()
    assert session.state_machine.state == TaskState.PENDING
    assert session.state_machine.metadata.get("transition_trigger") == "user_restart"
