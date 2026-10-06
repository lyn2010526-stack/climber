"""Backend reliability: durable run-progress snapshots for crash recovery."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import AgentEventType, ChatResult
from app.core.agent_engine import AgentEngine
from app.core.checkpoint import InMemoryCheckpointStore
from app.core.engine.run_progress import (
    RunProgressStore,
    build_loop_snapshot,
    record_loop_progress,
    _now,
)
from app.core.engine.run_storage import RunStorage
from app.core.session import AgentSession, SessionConfig
from app.storage import Base
from app.storage.database import (
    Agent,
    Message,
    RunProgressRecord,
    Session,
    SessionInput,
    Turn,
    UsageLog,
)
from app.storage.models_cost import CostRecord
from app.tools import ToolRegistry


class ScriptedModel:
    """An explicit fake model; no network or real LLM is exercised."""

    def __init__(self, responses, streaming=False):
        self.responses = iter(responses)
        self.capabilities = SimpleNamespace(streaming=streaming, max_tokens=100000)
        self.seen = []

    async def chat(self, messages, **kwargs):
        self.seen.append(list(messages))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response

    async def stream_chat(self, messages, **kwargs):
        self.seen.append(list(messages))
        for chunk in next(self.responses):
            if isinstance(chunk, Exception):
                raise chunk
            yield chunk


TABLES = (
    Agent,
    Session,
    SessionInput,
    Turn,
    Message,
    UsageLog,
    CostRecord,
    RunProgressRecord,
)


class RunProgressStoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="run-progress-")
        self.addCleanup(self.tmp.cleanup)
        self.db_engine = create_async_engine("sqlite+aiosqlite:///" + str(Path(self.tmp.name) / "progress.db"))
        self.addAsyncCleanup(self.db_engine.dispose)
        self.factory = async_sessionmaker(self.db_engine, expire_on_commit=False)
        async with self.db_engine.begin() as conn:
            await conn.run_sync(lambda db: Base.metadata.create_all(db, tables=[t.__table__ for t in TABLES]))
        self.store = RunProgressStore(self.factory)

    async def test_record_and_read_snapshot(self):
        ok = await self.store.record_progress(
            "s1", user_id="u1", turn_id="t1",
            outer_round=3, current_subtask="subtask-b",
            completed_subtasks=["subtask-a", "subtask-b"],
            followup_queue=["next-step", "after-step"],
            steering_queue=["steer"],
        )
        self.assertTrue(ok)
        snapshot = await self.store.get_progress("s1")
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["status"], "in_progress")
        self.assertEqual(snapshot["outer_round"], 3)
        self.assertEqual(snapshot["current_subtask"], "subtask-b")
        self.assertEqual(snapshot["completed_subtasks"], ["subtask-a", "subtask-b"])
        self.assertEqual(snapshot["followup_queue"], ["next-step", "after-step"])
        self.assertEqual(snapshot["steering_queue"], ["steer"])
        self.assertEqual(snapshot["user_id"], "u1")

    async def test_record_upserts_latest_snapshot(self):
        await self.store.record_progress("s1", user_id="u1", outer_round=1, current_subtask="one", completed_subtasks=["one"])
        await self.store.record_progress("s1", user_id="u1", outer_round=2, current_subtask="two", completed_subtasks=["one", "two"])
        rows = await self.store.get_progress("s1")
        self.assertEqual(rows["outer_round"], 2)
        self.assertEqual(rows["current_subtask"], "two")
        self.assertEqual(rows["completed_subtasks"], ["one", "two"])
        in_progress = await self.store.list_in_progress(user_id="u1")
        self.assertEqual(len(in_progress), 1)

    async def test_mark_completed_and_interrupted(self):
        await self.store.record_progress("c", user_id="u1", outer_round=1, current_subtask="t")
        self.assertTrue(await self.store.mark_completed("c"))
        self.assertEqual((await self.store.get_progress("c"))["status"], "completed")
        await self.store.record_progress("i", user_id="u1", outer_round=1, current_subtask="t")
        self.assertTrue(await self.store.mark_interrupted("i", reason="crashed mid-run"))
        snapshot = await self.store.get_progress("i")
        self.assertEqual(snapshot["status"], "interrupted")
        self.assertEqual(snapshot["current_subtask"], "crashed mid-run")

    async def test_stale_in_progress_marked_interrupted(self):
        await self.store.record_progress("fresh", user_id="u1", outer_round=2)
        await self.store.record_progress("stale", user_id="u1", outer_round=1)
        async with self.factory() as db:
            row = await db.get(RunProgressRecord, "stale")
            row.heartbeat_at = _now() - timedelta(minutes=60)
            await db.commit()
        await self.store.mark_completed("fresh")
        marked = await self.store.mark_stale_interrupted(max_age_minutes=10)
        self.assertEqual(marked, 1)
        self.assertEqual((await self.store.get_progress("stale"))["status"], "interrupted")
        self.assertEqual((await self.store.get_progress("fresh"))["status"], "completed")

    async def test_missing_table_fails_open(self):
        tmp = tempfile.TemporaryDirectory(prefix="run-progress-nosan-")
        self.addCleanup(tmp.cleanup)
        engine = create_async_engine("sqlite+aiosqlite:///" + str(Path(tmp.name) / "empty.db"))
        self.addAsyncCleanup(engine.dispose)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(lambda db: Base.metadata.create_all(db, tables=[Session.__table__]))
        store = RunProgressStore(factory)
        self.assertFalse(await store.record_progress("s1", outer_round=1))
        self.assertIsNone(await store.get_progress("s1"))
        self.assertEqual(await store.list_in_progress(), [])

    async def test_loop_snapshot_builder(self):
        session = SimpleNamespace(
            session_id="s1", user_id="u1", current_turn_id="t1",
        )
        payload = {
            "outer_round": 4,
            "current_input": "subtask-4",
            "completed": ["a", "b"],
            "followup_queue": ["c"],
            "steering_queue": [],
        }
        snapshot = build_loop_snapshot(session, payload)
        self.assertEqual(snapshot["outer_round"], 4)
        self.assertEqual(snapshot["current_subtask"], "subtask-4")
        self.assertEqual(snapshot["completed_subtasks"], ["a", "b"])
        self.assertEqual(snapshot["steering_queue"], [])


class EngineWiringTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="run-progress-engine-")
        self.addCleanup(self.tmp.cleanup)
        self.db_engine = create_async_engine("sqlite+aiosqlite:///" + str(Path(self.tmp.name) / "engine.db"))
        self.addAsyncCleanup(self.db_engine.dispose)
        self.factory = async_sessionmaker(self.db_engine, expire_on_commit=False)
        async with self.db_engine.begin() as conn:
            await conn.run_sync(lambda db: Base.metadata.create_all(db, tables=[t.__table__ for t in TABLES]))
        async with self.factory() as db:
            db.add(Session(id="s", user_id="u", context_data={}))
            await db.commit()
        self.store = RunProgressStore(self.factory)
        self.patches = [
            patch("app.storage.async_session", self.factory),
            patch("app.core.ui_rules.refresh_rule_context", AsyncMock()),
            patch("app.core.prompt_optimizer.maybe_optimize_instruction", AsyncMock()),
            patch.object(AgentEngine, "_init_reasoning", Mock()),
            patch.object(AgentEngine, "_init_sandbox", Mock()),
            patch.object(AgentEngine, "_init_permissions", Mock()),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def engine(self, responses):
        model = ScriptedModel(responses)
        registry = ToolRegistry()
        engine = AgentEngine(
            model_registry=SimpleNamespace(get_or_create=lambda **_kwargs: model),
            tool_registry=registry,
            checkpoint_store=InMemoryCheckpointStore(),
            run_store=RunStorage(self.factory),
        )
        engine.sandbox = engine.permission_overlay = engine.agent_mode = None
        engine._validate_tool_call = Mock(return_value=(True, "scripted test tool"))
        engine._build_tools_for_session = Mock(return_value=[])
        for name in ("_set_agent_mode", "_send_start_notification", "_send_completion_notification",
                     "_send_failure_notification", "_trigger_memory_reflection", "_record_profile_outcome",
                     "_tick_evolution"):
            setattr(engine, name, Mock())
        for name in ("_inject_memory_context", "_inject_core_memory", "_inject_profile_context",
                     "_store_episodic_memory", "_archive_instruction"):
            setattr(engine, name, AsyncMock())
        session = AgentSession(SessionConfig(session_id="s", user_id="u", agent_id="",
                                             provider="scripted", model_id="fake"))
        return engine, session, model

    async def test_loop_records_progress_and_finalizes_completed(self):
        await self.engine_submit()
        engine, session, _ = self.engine([ChatResult(content="first")])
        events = [event async for event in engine.run(session, "initial")]
        self.assertEqual(events[-1].type, AgentEventType.DONE)
        snapshot = await self.store.get_progress("s")
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["outer_round"], 1)
        self.assertEqual(snapshot["current_subtask"], "initial")
        self.assertEqual(snapshot["completed_subtasks"], ["initial"])

    async def test_interrupted_marking_when_followup_turn_fails(self):
        await self.engine_submit()
        await self.engine_submit("followup-1", kind="follow_up")
        engine, session, _ = self.engine([ChatResult(content="first"), RuntimeError("boom")])
        try:
            events = [event async for event in engine.run(session, "initial")]
        except RuntimeError:
            events = []
        snapshot = await self.store.get_progress("s")
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["status"], "interrupted")
        self.assertIn("boom", snapshot["current_subtask"])

    async def test_no_progress_pause_marks_interrupted(self):
        await self.engine_submit()
        await self.engine_submit("later", kind="follow_up")
        engine, session, _ = self.engine([ChatResult(), ChatResult()])
        events = [event async for event in engine.run(session, "initial")]
        self.assertEqual(events[-1].data["status"], "no_progress")
        snapshot = await self.store.get_progress("s")
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["status"], "interrupted")

    async def engine_submit(self, request_id="first", kind="steering"):
        from app.core.engine.input_queue import SessionInputQueue

        queue = SessionInputQueue(self.factory)
        await queue.submit("s", "u", request_id, kind, request_id)


class HelperTests(unittest.IsolatedAsyncioTestCase):
    async def test_record_loop_progress_uses_engine_factory(self):
        tmp = tempfile.TemporaryDirectory(prefix="run-progress-helper-")
        self.addCleanup(tmp.cleanup)
        db_engine = create_async_engine("sqlite+aiosqlite:///" + str(Path(tmp.name) / "h.db"))
        self.addAsyncCleanup(db_engine.dispose)
        factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with db_engine.begin() as conn:
            await conn.run_sync(lambda db: Base.metadata.create_all(db, tables=[t.__table__ for t in TABLES]))
        engine = SimpleNamespace(_run_store=SimpleNamespace(session_factory=factory))
        session = SimpleNamespace(session_id="s", user_id="u", current_turn_id="t")
        payload = {"outer_round": 2, "current_input": "step", "completed": ["step"],
                   "followup_queue": [], "steering_queue": []}
        self.assertTrue(await record_loop_progress(engine, session, payload))
        store = RunProgressStore(factory)
        snapshot = await store.get_progress("s")
        self.assertEqual(snapshot["outer_round"], 2)