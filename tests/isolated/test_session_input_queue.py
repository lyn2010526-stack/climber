"""Private SQLite integration tests with a scripted model and real engine/HTTP routes."""

import asyncio
import json
import socket
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import AgentEventType, ChatResult
from app.core.agent_engine import AgentEngine
from app.core.checkpoint import InMemoryCheckpointStore
from app.core.engine.input_queue import SessionInputQueue, stalled_batch
from app.core.engine.run_storage import RunStorage
from app.core.session import AgentSession, SessionConfig
from app.storage import Base
from app.storage.database import Agent, Message, Session, SessionInput, Turn, UsageLog
from app.storage.models_cost import CostRecord
from app.tools import ToolRegistry


class QueueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="session-input-queue-")
        self.db_engine = create_async_engine("sqlite+aiosqlite:///" + str(Path(self.tmp.name) / "private.db"))
        self.factory = async_sessionmaker(self.db_engine, expire_on_commit=False)
        tables = [m.__table__ for m in (Agent, Session, SessionInput, Turn, Message, UsageLog, CostRecord)]
        async with self.db_engine.begin() as conn:
            await conn.run_sync(lambda db: Base.metadata.create_all(db, tables=tables))
        self.queue = SessionInputQueue(self.factory)
        async with self.factory() as db:
            db.add(Session(id="s", user_id="u", context_data={}))
            await db.commit()
        self.patches = []
        for target, value in (
            ("app.storage.async_session", self.factory),
            ("app.core.ui_rules.refresh_rule_context", AsyncMock()),
            ("app.core.prompt_optimizer.maybe_optimize_instruction", AsyncMock()),
            ("app.core.agent_engine.AgentEngine._init_reasoning", Mock()),
            ("app.core.agent_engine.AgentEngine._init_sandbox", Mock()),
            ("app.core.agent_engine.AgentEngine._init_permissions", Mock()),
        ):
            p = patch(target, value)
            p.start()
            self.patches.append(p)

    async def asyncTearDown(self):
        for p in reversed(self.patches):
            p.stop()
        await self.db_engine.dispose()
        self.tmp.cleanup()

    async def submit(self, request_id, kind="follow_up", message=None):
        return await self.queue.submit("s", "u", request_id, kind, message or request_id)

    def engine(self, responses):
        owner = self

        class ScriptedModel:
            capabilities = SimpleNamespace(streaming=False, max_tokens=100000)

            def __init__(self):
                self.responses = iter(responses)
                self.seen = []

            async def chat(self, messages, **_kwargs):
                self.seen.append([dict(m) for m in messages])
                value = next(self.responses)
                return await value(owner) if callable(value) else value

        model = ScriptedModel()
        registry = ToolRegistry()
        engine = AgentEngine(model_registry=SimpleNamespace(get_or_create=lambda **_kwargs: model),
                             tool_registry=registry, checkpoint_store=InMemoryCheckpointStore(),
                             run_store=RunStorage(self.factory))
        engine.sandbox = engine.permission_overlay = engine.agent_mode = None
        engine._validate_tool_call = Mock(return_value=(True, "scripted test tool"))
        engine._build_tools_for_session = Mock(return_value=[])
        for name in ("_set_agent_mode", "_send_start_notification", "_send_completion_notification",
                     "_send_failure_notification", "_trigger_memory_reflection", "_record_profile_outcome", "_tick_evolution"):
            setattr(engine, name, Mock())
        for name in ("_inject_memory_context", "_inject_core_memory", "_inject_profile_context",
                     "_store_episodic_memory", "_archive_instruction"):
            setattr(engine, name, AsyncMock())
        session = AgentSession(SessionConfig(session_id="s", user_id="u", agent_id="",
                                             provider="scripted", model_id="fake"))
        return engine, session, model

    async def test_concurrent_idempotency_fifo_and_conflict(self):
        items = await asyncio.gather(*(self.submit("same") for _ in range(8)))
        self.assertEqual(len({item["id"] for item in items}), 1)
        await asyncio.gather(*(self.submit(str(i)) for i in range(8)))
        rows = await self.queue.list("s", "u")
        self.assertEqual([r["sequence"] for r in rows], list(range(1, 10)))
        with self.assertRaises(ValueError):
            await self.submit("same", message="changed")
        for row in rows:
            claimed = await self.queue.claim("s", "u", "follow_up")
            self.assertEqual(claimed["id"], row["id"])
            await self.queue.finish("s", "u", claimed["id"], "completed")

    async def test_ownership_freeze_and_restart(self):
        with self.assertRaises(LookupError):
            await self.queue.submit("s", "other", "x", "steering", "x")
        await self.submit("a")
        await self.submit("b")
        await self.queue.claim("s", "u", "follow_up")
        restored = SessionInputQueue(self.factory)
        blocked = await restored.recover("s", "u")
        self.assertEqual([i["status"] for i in blocked], ["blocked", "blocked"])
        self.assertEqual((await self.submit("c"))["status"], "blocked")
        self.assertIsNone(await restored.claim("s", "u", "follow_up"))

    async def test_followups_turn_commit_and_single_done(self):
        async def enqueue(owner):
            await owner.submit("a")
            await owner.submit("b")
            return ChatResult(content="first")

        engine, session, model = self.engine([enqueue, ChatResult(content="second"), ChatResult(content="third")])
        events = []
        async for event in engine.run(session, "initial"):
            events.append(event)
            if event.type == AgentEventType.TURN_DONE:
                async with self.factory() as db:
                    turn = await db.get(Turn, event.data["turn_id"])
                    self.assertEqual(turn.status, "completed")
                    self.assertIsNotNone(turn.completed_at)
                    message = await db.get(Message, event.data["message_id"])
                    self.assertEqual(message.role, "assistant")
                    self.assertEqual(message.content, ["first", "second", "third"][
                        sum(e.type == AgentEventType.TURN_DONE for e in events) - 1])
        self.assertEqual(sum(e.type == AgentEventType.DONE for e in events), 1)
        self.assertEqual(sum(e.type == AgentEventType.TURN_STARTED for e in events), 3)
        self.assertEqual([i["status"] for i in await self.queue.list("s", "u")], ["completed", "completed"])
        self.assertTrue(any(m["content"] == "a" for m in model.seen[1]))
        self.assertTrue(any(m["content"] == "b" for m in model.seen[2]))

    async def test_steering_arriving_during_tool_consumed_after_batch(self):
        call = {"id": "t", "function": {"name": "read_file", "arguments": "{}"}}
        engine, session, model = self.engine([ChatResult(tool_calls=[call]), ChatResult(content="answer")])

        async def read_file():
            await self.submit("steer", "steering", "change direction")
            return "file content"

        engine.tool_registry.register("read_file", "read", {"type": "object"}, read_file)
        events = [e async for e in engine.run(session, "initial")]
        self.assertTrue(any(m["content"] == "change direction" for m in model.seen[1]))
        self.assertEqual((await self.queue.list("s", "u"))[0]["status"], "applied")
        applied = next(i for i, e in enumerate(events) if e.type == AgentEventType.INPUT_STATUS and e.data["item"]["status"] == "applied")
        tool_result = next(i for i, e in enumerate(events) if e.type == AgentEventType.TOOL_RESULT)
        self.assertGreater(applied, tool_result)

    async def test_two_empty_responses_pause_and_freeze(self):
        await self.submit("later")
        engine, session, _ = self.engine([ChatResult(), ChatResult()])
        events = [e async for e in engine.run(session, "initial")]
        self.assertEqual(session.status.value, "paused")
        self.assertEqual(events[-1].data["status"], "no_progress")
        self.assertEqual((await self.queue.list("s", "u"))[0]["status"], "blocked")
        async with self.factory() as db:
            self.assertEqual((await db.scalar(select(Turn))).status, "paused")

    async def test_followup_no_progress_preserves_blocked_and_final_done(self):
        await self.submit("active")
        await self.submit("later")
        engine, session, _ = self.engine([ChatResult(content="first"), ChatResult(), ChatResult()])
        events = [e async for e in engine.run(session, "initial")]
        self.assertEqual([i["status"] for i in await self.queue.list("s", "u")], ["blocked", "blocked"])
        self.assertEqual(events[-1].type, AgentEventType.DONE)
        self.assertEqual(events[-1].data["status"], "no_progress")
        self.assertFalse(any(e.type == AgentEventType.ERROR for e in events))

    async def test_followup_user_pause_preserves_paused_turn_and_done(self):
        await self.submit("active")
        await self.submit("later")

        async def pause(_owner):
            await session.pause()
            return ChatResult(content="arrived after pause")

        engine, session, _ = self.engine([ChatResult(content="first"), pause])
        events = [e async for e in engine.run(session, "initial")]
        self.assertEqual(events[-1].data["status"], "paused")
        self.assertEqual([i["status"] for i in await self.queue.list("s", "u")], ["blocked", "blocked"])
        self.assertFalse(any(e.type == AgentEventType.ERROR for e in events))
        async with self.factory() as db:
            self.assertEqual((await db.get(Turn, session.current_turn_id)).status, "paused")

    async def test_followup_user_stop_is_blocked_and_emits_stopped_done(self):
        await self.submit("active")
        await self.submit("later")

        async def stop(_owner):
            session.stop()
            await asyncio.sleep(0)
            return ChatResult(content="arrived after stop")

        engine, session, _ = self.engine([ChatResult(content="first"), stop])
        events = [e async for e in engine.run(session, "initial")]
        self.assertEqual(events[-1].type, AgentEventType.DONE)
        self.assertEqual(events[-1].data["status"], "stopped")
        self.assertEqual([i["status"] for i in await self.queue.list("s", "u")], ["blocked", "blocked"])

    async def test_freeze_during_followup_keeps_blocked_without_false_failure(self):
        await self.submit("active")

        async def freeze(owner):
            await owner.queue.freeze("s", "u", "external safety freeze")
            return ChatResult(content="finished response")

        engine, session, _ = self.engine([ChatResult(content="first"), freeze])
        events = [e async for e in engine.run(session, "initial")]
        self.assertEqual(events[-1].type, AgentEventType.DONE)
        self.assertFalse(any(e.type == AgentEventType.ERROR for e in events))
        self.assertEqual((await self.queue.list("s", "u"))[0]["status"], "blocked")

    async def test_startup_creates_queue_and_preserves_existing_session(self):
        import app.storage as storage

        startup_engine = create_async_engine("sqlite+aiosqlite:///" + str(Path(self.tmp.name) / "startup.db"))
        factory = async_sessionmaker(startup_engine, expire_on_commit=False)
        try:
            async with startup_engine.begin() as conn:
                await conn.run_sync(lambda db: Session.__table__.create(db))
            async with factory() as db:
                db.add(Session(id="existing", user_id="u", title="preserved"))
                await db.commit()
            with patch.object(storage, "engine", startup_engine):
                await storage.init_db()
                await storage.init_db()
            async with factory() as db:
                self.assertEqual((await db.get(Session, "existing")).title, "preserved")
            item = await SessionInputQueue(factory).submit("existing", "u", "a", "follow_up", "hello")
            self.assertEqual(item["status"], "queued")
        finally:
            await startup_engine.dispose()

    async def test_finish_is_idempotent_and_cannot_overwrite_frozen_input(self):
        item = await self.submit("active")
        await self.queue.claim("s", "u", "follow_up")
        await self.queue.freeze("s", "u", "manual review")
        result = await self.queue.finish("s", "u", item["id"], "completed")
        self.assertEqual((result["status"], result["error"]), ("blocked", "manual review"))

    async def test_review_resume_only_requeues_persistently_unstarted_inputs(self):
        active = await self.submit("active")
        later = await self.submit("later")
        await self.queue.claim("s", "u", "follow_up")
        await self.queue.recover("s", "u")
        fresh = await self.submit("fresh")
        await self.queue.freeze("s", "u", "another freeze")
        restored = SessionInputQueue(self.factory)
        with self.assertRaises(ValueError):
            await restored.resume_reviewed("s", "u", False)
        with self.assertRaises(LookupError):
            await restored.resume_reviewed("s", "other", True)
        items = await restored.resume_reviewed("s", "u", True)
        self.assertEqual([i["status"] for i in items], ["blocked", "queued", "queued"])
        self.assertEqual(items[0]["id"], active["id"])
        self.assertIn("unknown effects", items[0]["error"])
        self.assertEqual((await restored.claim("s", "u", "follow_up"))["id"], later["id"])
        await restored.finish("s", "u", later["id"], "completed")
        self.assertEqual((await restored.claim("s", "u", "follow_up"))["id"], fresh["id"])

    async def test_legacy_blocked_input_without_safety_evidence_stays_blocked(self):
        item = await self.submit("legacy")
        async with self.factory() as db:
            row = await db.get(SessionInput, item["id"])
            row.status = "blocked"
            session = await db.get(Session, "s")
            session.context_data = {"input_queue_frozen": "legacy freeze"}
            await db.commit()
        items = await self.queue.resume_reviewed("s", "u", True)
        self.assertEqual(items[0]["status"], "blocked")

    async def test_runtime_report_uses_committed_queue_states(self):
        completed = await self.submit("completed")
        await self.queue.claim("s", "u", "follow_up")
        await self.queue.finish("s", "u", completed["id"], "completed")
        await self.submit("executing")
        await self.queue.claim("s", "u", "follow_up")
        await self.submit("queued")
        self.assertEqual(await self.queue.report("s", "u"), {
            "completed": ["completed"], "executing": ["executing"], "queued": ["queued"], "risks": [],
        })
        await self.queue.freeze("s", "u", "unknown effects")
        report = await self.queue.report("s", "u")
        self.assertEqual(report["executing"], [])
        self.assertEqual(report["queued"], [])
        self.assertEqual(report["risks"], ["executing: unknown effects", "queued: unknown effects"])
        with self.assertRaises(LookupError):
            await self.queue.report("s", "other")

    async def test_runtime_report_stream_matches_final_persistent_snapshot(self):
        await self.submit("a")
        engine, session, _ = self.engine([ChatResult(content="first"), ChatResult(content="second")])
        events = [e async for e in engine.run(session, "initial")]
        reports = [e.data for e in events if e.type == AgentEventType.RUNTIME_REPORT]
        self.assertEqual(reports[0]["executing"], ["initial"])
        self.assertEqual(reports[-1], await self.queue.report("s", "u"))
        self.assertEqual(reports[-1]["completed"], ["a"])

    async def test_steering_during_final_response_gets_another_iteration(self):
        async def steer(owner):
            await owner.submit("late", "steering", "new direction")
            return ChatResult(content="initial answer")

        engine, session, model = self.engine([steer, ChatResult(content="revised answer")])
        events = [e async for e in engine.run(session, "initial")]
        self.assertEqual(len(model.seen), 2)
        self.assertEqual((await self.queue.list("s", "u"))[0]["status"], "applied")
        self.assertEqual(sum(e.type == AgentEventType.DONE for e in events), 1)

    async def test_changed_read_observations_reset_no_progress(self):
        calls = [{"id": str(i), "function": {"name": "read_file", "arguments": "{}"}} for i in range(5)]
        engine, session, _ = self.engine([*(ChatResult(tool_calls=[c]) for c in calls), ChatResult(content="done")])
        observations = iter(["one", "one", "two", "two", "three"])
        engine.tool_registry.register("read_file", "read", {"type": "object"}, lambda: next(observations))
        events = [e async for e in engine.run(session, "initial")]
        self.assertEqual(session.status.value, "completed")
        self.assertEqual(events[-1].type, AgentEventType.DONE)

    async def test_empty_response_after_one_repeated_read_is_not_two_empty_rounds(self):
        calls = [{"id": str(i), "function": {"name": "read_file", "arguments": "{}"}} for i in range(2)]
        engine, session, _ = self.engine([*(ChatResult(tool_calls=[c]) for c in calls), ChatResult(), ChatResult(content="done")])
        engine.tool_registry.register("read_file", "read", {"type": "object"}, lambda: "same")
        events = [e async for e in engine.run(session, "initial")]
        self.assertEqual(session.status.value, "completed")
        self.assertEqual(events[-1].type, AgentEventType.DONE)

    async def test_followup_failure_status_and_freeze(self):
        await self.submit("a")
        await self.submit("b")
        engine, session, model = self.engine([ChatResult(content="first"), ChatResult(finish_reason="error")])
        events = [e async for e in engine.run(session, "initial")]
        self.assertEqual([i["status"] for i in await self.queue.list("s", "u")], ["failed", "blocked"])
        self.assertEqual(len(model.seen), 2)
        self.assertTrue(any(e.type == AgentEventType.ERROR for e in events))
        self.assertEqual(events[-1].type, AgentEventType.DONE)

    async def test_commit_failure_never_returns_successful_submission(self):
        with patch("sqlalchemy.ext.asyncio.AsyncSession.commit", AsyncMock(side_effect=RuntimeError("commit rejected"))):
            with self.assertRaisesRegex(RuntimeError, "commit rejected"):
                await self.submit("failed-commit")
        self.assertEqual(await self.queue.list("s", "u"), [])

    async def test_followup_response_persistence_failure_is_failed(self):
        await self.submit("a")
        engine, session, _ = self.engine([ChatResult(content="first"), ChatResult(content="second")])
        original = engine._persist_message

        async def persist(sid, role, **kwargs):
            return None if kwargs.get("content") == "second" else await original(sid, role, **kwargs)

        engine._persist_message = persist
        events = [e async for e in engine.run(session, "initial")]
        item = (await self.queue.list("s", "u"))[0]
        self.assertEqual(item["status"], "failed")
        self.assertIn("persistence failed", item["error"])
        self.assertEqual(events[-1].type, AgentEventType.DONE)

    async def test_disconnect_freezes_inputs_and_preserves_busy_lock(self):
        await self.submit("a")
        engine, session, _ = self.engine([ChatResult(content="first")])
        stream = engine.run(session, "initial")
        await anext(stream)
        busy = [e async for e in engine.run(session, "second")]
        self.assertIn("busy", busy[0].data["error"])
        self.assertTrue(engine._session_locks["s"].locked())
        await stream.aclose()
        self.assertNotIn("s", engine._session_locks)
        self.assertEqual((await self.queue.list("s", "u"))[0]["status"], "blocked")

    async def test_migration_is_idempotent_on_private_sqlite(self):
        import importlib.util

        from alembic.migration import MigrationContext
        from alembic.operations import Operations

        path = Path(__file__).parents[2] / "alembic/versions/1b2c3d4e5f6a_session_input_queue.py"
        spec = importlib.util.spec_from_file_location("queue_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration_engine = create_async_engine("sqlite+aiosqlite:///" + str(Path(self.tmp.name) / "migration.db"))
        try:
            async with migration_engine.begin() as conn:
                def upgrade(db):
                    Session.__table__.create(db)
                    with Operations.context(MigrationContext.configure(db)):
                        migration.upgrade()
                        migration.upgrade()
                await conn.run_sync(upgrade)
            factory = async_sessionmaker(migration_engine, expire_on_commit=False)
            async with factory() as db:
                db.add(Session(id="s", user_id="u"))
                await db.commit()
            item = await SessionInputQueue(factory).submit("s", "u", "a", "follow_up", "hello")
            self.assertEqual(item["status"], "queued")
        finally:
            await migration_engine.dispose()

    async def test_repeated_read_results_pause_but_writes_progress(self):
        for name, expected in (("read_file", "paused"), ("write_file", "completed")):
            calls = [{"id": str(i), "function": {"name": name, "arguments": "{}"}} for i in range(3)]
            engine, session, _ = self.engine([*(ChatResult(tool_calls=[c]) for c in calls), ChatResult(content="done")])
            engine.tool_registry.register(name, name, {"type": "object"}, lambda: "unchanged")
            events = [e async for e in engine.run(session, "initial")]
            self.assertEqual(session.status.value, expected)
            self.assertEqual(sum(e.type == AgentEventType.DONE for e in events), 1)

    async def test_stop_at_turn_boundary_freezes_followups(self):
        await self.submit("later")
        engine, session, model = self.engine([ChatResult(content="first")])
        events = []
        async for event in engine.run(session, "initial"):
            events.append(event)
            if event.type == AgentEventType.TURN_DONE:
                session.stop()
        self.assertEqual(len(model.seen), 1)
        item = (await self.queue.list("s", "u"))[0]
        self.assertEqual(item["status"], "blocked")
        self.assertIsNotNone(item["error"])
        self.assertTrue(item["error"].strip())
        self.assertEqual(events[-1].data["status"], "stopped")

    async def test_stopped_claimed_input_always_records_error(self):
        await self.submit("first-followup")
        await self.submit("second-followup")
        engine, session, _ = self.engine([ChatResult(content="first"), ChatResult(content="second")])
        events = []
        turn_dones = 0
        async for event in engine.run(session, "initial"):
            events.append(event)
            if event.type == AgentEventType.TURN_DONE:
                turn_dones += 1
                if turn_dones == 1:
                    session.stop()
        items = {i["id"]: i for i in await self.queue.list("s", "u")}
        blocked = [i for i in items.values() if i["status"] == "blocked"]
        self.assertTrue(blocked)
        for item in blocked:
            self.assertIsNotNone(item["error"])
            self.assertTrue(item["error"].strip())
        report = await self.queue.report("s", "u")
        self.assertFalse(any(text.endswith(": blocked") for text in report["risks"] + report["queued"]))

    async def test_persistence_failure_never_acknowledges_applied(self):
        await self.submit("steer", "steering")
        engine, session, model = self.engine([ChatResult(content="answer")])
        original = engine._persist_message

        async def persist(sid, role, **kwargs):
            return None if kwargs.get("content") == "steer" else await original(sid, role, **kwargs)

        engine._persist_message = persist
        events = [e async for e in engine.run(session, "initial")]
        self.assertEqual(model.seen, [])
        self.assertFalse(any(e.type == AgentEventType.INPUT_STATUS and e.data["item"]["status"] == "applied" for e in events))
        self.assertEqual((await self.queue.list("s", "u"))[0]["status"], "blocked")

    async def test_http_contract_validation_and_ownership(self):
        from app.api.v1 import sessions

        app = FastAPI()
        app.include_router(sessions.router, prefix="/api/v1/sessions")
        app.dependency_overrides[sessions.get_current_user] = lambda: "u"
        for route in app.routes:
            for dependency in getattr(getattr(route, "dependant", None), "dependencies", []):
                if dependency.name == "_auth":
                    app.dependency_overrides[dependency.call] = dict
        with patch.object(sessions, "async_session", self.factory):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                payload = {"client_request_id": "a", "kind": "steering", "message": "hello"}
                response = await client.post("/api/v1/sessions/s/inputs", json=payload)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["status"], "queued")
                self.assertEqual((await client.post("/api/v1/sessions/s/inputs", json=payload)).json(), response.json())
                self.assertEqual((await client.get("/api/v1/sessions/s/inputs")).json()["items"], [response.json()])
                report = await client.get("/api/v1/sessions/s/inputs/report")
                self.assertEqual(report.status_code, 200, report.text)
                self.assertEqual(report.json(), {"completed": [], "executing": [], "queued": ["hello"], "risks": []})
                self.assertEqual((await client.post("/api/v1/sessions/s/inputs", json={**payload, "message": "different"})).status_code, 409)
                self.assertEqual((await client.post("/api/v1/sessions/s/inputs", json={**payload, "kind": "invalid"})).status_code, 422)
                await self.queue.freeze("s", "u", "review required")
                for review in ({}, {"review_confirmed": False}):
                    self.assertEqual((await client.post("/api/v1/sessions/s/inputs/resume", json=review)).status_code, 422)
                reviewed = await client.post("/api/v1/sessions/s/inputs/resume", json={"review_confirmed": True})
                self.assertEqual(reviewed.status_code, 200, reviewed.text)
                self.assertEqual(reviewed.json()["items"][0]["status"], "queued")
                app.dependency_overrides[sessions.get_current_user] = lambda: "other"
                self.assertEqual((await client.get("/api/v1/sessions/s/inputs/report")).status_code, 404)
                self.assertEqual((await client.post("/api/v1/sessions/s/inputs/resume", json={"review_confirmed": True})).status_code, 404)
                self.assertEqual((await client.get("/api/v1/sessions/s/inputs")).status_code, 404)
                self.assertEqual((await client.post("/api/v1/sessions/s/inputs", json=payload)).status_code, 404)

    async def test_real_http_sse_interleaves_post_inputs_and_persistent_contracts(self):
        import uvicorn

        from app.api.v1 import chat, sessions

        entered, release = asyncio.Event(), asyncio.Event()

        async def blocked_response(_owner):
            entered.set()
            await asyncio.wait_for(release.wait(), 10)
            return ChatResult(content="first answer")

        engine, session, model = self.engine([
            blocked_response, ChatResult(content="steered answer"), ChatResult(content="follow-up answer"),
        ])
        engine._sessions["s"] = session
        async with self.factory() as db:
            agent = Agent(id="http-agent", user_id="u", name="scripted HTTP", provider="ollama",
                          model_id="scripted", api_key_encrypted="")
            db.add(agent)
            row = await db.get(Session, "s")
            row.agent_id = agent.id
            await db.commit()
        app = FastAPI()
        app.include_router(chat.router, prefix="/api/v1/sessions")
        app.include_router(sessions.router, prefix="/api/v1/sessions")
        app.dependency_overrides[chat.get_current_user] = lambda: "u"
        for router in (chat.router, sessions.router):
            for route in router.routes:
                for dependency in route.dependant.dependencies:
                    if dependency.name in {"_auth", "_scope_check"}:
                        app.dependency_overrides[dependency.call] = lambda: {}
        registry = SimpleNamespace(get_default=lambda: model, get_or_create=lambda **kwargs: model)
        frames = []
        first_frame = asyncio.Event()
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, lifespan="off", log_level="error"))
        server_task = None
        stream_task = None
        with patch.object(chat, "async_session", self.factory), patch.object(sessions, "async_session", self.factory), \
                patch.object(chat, "get_engine", return_value=engine), \
                patch.object(chat, "_ChatModelRegistry", return_value=registry):
            try:
                server_task = asyncio.create_task(server.serve(sockets=[sock]))
                async with asyncio.timeout(10):
                    while not server.started:
                        if server_task.done():
                            await server_task
                            self.fail("HTTP test server exited before startup")
                        await asyncio.sleep(0.01)
                async with AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=15) as client:
                    async def consume():
                        async with client.stream("POST", "/api/v1/sessions/s/chat", json={"message": "initial"}) as response:
                            self.assertEqual(response.status_code, 200)
                            self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
                            event_name = None
                            async for line in response.aiter_lines():
                                if line.startswith("event: "):
                                    event_name = line[7:]
                                elif line.startswith("data: "):
                                    frames.append((event_name, json.loads(line[6:])))
                                    first_frame.set()

                    stream_task = asyncio.create_task(consume())
                    await asyncio.wait_for(first_frame.wait(), 10)
                    await asyncio.wait_for(entered.wait(), 10)
                    self.assertFalse(stream_task.done())
                    posted = []
                    for kind, message in (("steering", "change direction"), ("follow_up", "next task")):
                        response = await client.post("/api/v1/sessions/s/inputs", json={
                            "client_request_id": kind, "kind": kind, "message": message,
                        })
                        self.assertEqual(response.status_code, 200, response.text)
                        item = response.json()
                        self.assertNotIn("item", item)
                        self.assertEqual(item["status"], "queued")
                        self.assertIsInstance(item["id"], str)
                        posted.append(item)
                    page = await client.get("/api/v1/sessions/s/inputs")
                    self.assertEqual(page.json(), {"items": posted})
                    self.assertFalse(stream_task.done())
                    release.set()
                    await asyncio.wait_for(stream_task, 15)
                    final_page = (await client.get("/api/v1/sessions/s/inputs")).json()
                    self.assertEqual([i["status"] for i in final_page["items"]], ["applied", "completed"])
                    snapshot = (await client.get("/api/v1/sessions/s/inputs/report")).json()
                reports = [data for name, data in frames if name == "runtime_report"]
                self.assertTrue(reports)
                for report in [*reports, snapshot]:
                    self.assertEqual(set(report), {"completed", "executing", "queued", "risks"})
                    for values in report.values():
                        self.assertIsInstance(values, list)
                        self.assertTrue(all(isinstance(value, str) for value in values))
                self.assertEqual(reports[-1], snapshot)
                turns = [data for name, data in frames if name == "turn_done"]
                self.assertEqual(len(turns), 2)
                async with self.factory() as db:
                    for data, content in zip(turns, ("steered answer", "follow-up answer"), strict=True):
                        self.assertIsInstance(data["message_id"], str)
                        message = await db.get(Message, data["message_id"])
                        self.assertEqual((message.session_id, message.role, message.content), ("s", "assistant", content))
                        self.assertEqual((await db.get(Turn, data["turn_id"])).status, "completed")
                self.assertTrue(any(m["content"] == "change direction" for m in model.seen[1]))
                self.assertTrue(any(m["content"] == "next task" for m in model.seen[2]))
                self.assertEqual(sum(name == "done" for name, _ in frames), 1)
                self.assertEqual(frames[-1][0], "done")
                self.assertFalse(any(name == "error" for name, _ in frames))
                print("HTTP_SSE_EVIDENCE=" + json.dumps({
                    "transport": "real loopback HTTP / FastAPI / Uvicorn", "post_items": posted,
                    "get_items": final_page, "runtime_report": snapshot, "turn_done": turns,
                    "event_order": [name for name, _ in frames],
                }, sort_keys=True))
            finally:
                release.set()
                if stream_task is not None and not stream_task.done():
                    stream_task.cancel()
                    await asyncio.gather(stream_task, return_exceptions=True)
                server.should_exit = True
                if server_task is not None:
                    await asyncio.wait_for(server_task, 10)
                sock.close()

    async def test_review_resume_requires_write_scope_dependency(self):
        from fastapi import HTTPException

        from app.api.v1 import sessions

        app = FastAPI()
        app.include_router(sessions.router, prefix="/api/v1/sessions")
        app.dependency_overrides[sessions.get_current_user] = lambda: "u"

        def deny_write():
            raise HTTPException(403, detail="write scope required")

        route = next(r for r in sessions.router.routes if getattr(r, "path", "").endswith("/inputs/resume"))
        auth = next(d.call for d in route.dependant.dependencies if d.name == "_auth")
        app.dependency_overrides[auth] = deny_write
        with patch.object(sessions, "async_session", self.factory):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/sessions/s/inputs/resume", json={"review_confirmed": True})
                self.assertEqual(response.status_code, 403)

    def test_progress_evidence_requires_same_call_and_nonempty_observation(self):
        call = {"id": "a", "function": {"name": "read_file", "arguments": "{}"}}
        self.assertIsNone(stalled_batch([call], [{"id": "a", "result": "", "error": None}]))
        self.assertIsNone(stalled_batch([call], [{"id": "a", "result": "same", "error": "denied"}]))
        self.assertIsNotNone(stalled_batch([call], [{"id": "a", "result": "same", "error": None}]))

    def test_progress_evidence_rejects_ambiguous_or_malformed_correlations(self):
        call = {"id": "a", "function": {"name": "read_file", "arguments": "{}"}}
        other = {**call, "id": "b"}
        result = {"id": "a", "result": "same", "error": None}
        for calls, results in (
            ([call, call], [result, {**result, "id": "b"}]),
            ([call, other], [result, result]),
            ([{**call, "id": None}], [{**result, "id": None}]),
            ([{**call, "id": ""}], [{**result, "id": ""}]),
            ([call], [{**result, "id": "other"}]),
            ([{**call, "function": None}], [result]),
            ([{**call, "function": {"name": "read_file", "arguments": "[]"}}], [result]),
            ([{**call, "function": {"name": "read_file", "arguments": None}}], [result]),
        ):
            with self.subTest(calls=calls, results=results):
                self.assertIsNone(stalled_batch(calls, results))

    def test_progress_evidence_matches_ids_and_normalizes_argument_objects(self):
        calls = [
            {"id": "a", "function": {"name": "read_file", "arguments": '{"path":"a","offset":0}'}},
            {"id": "b", "function": {"name": "read_file", "arguments": {"path": "b"}}},
        ]
        results = [{"id": "b", "result": "second"}, {"id": "a", "result": "first"}]
        evidence = stalled_batch(calls, results)
        self.assertIsNotNone(evidence)
        changed_ids = [{**call, "id": str(i)} for i, call in enumerate(calls)]
        changed_ids[0] = {**changed_ids[0], "function": {
            "name": "read_file", "arguments": {"offset": 0, "path": "a"},
        }}
        self.assertEqual(evidence, stalled_batch(changed_ids, [
            {"id": "0", "result": "first"}, {"id": "1", "result": "second"},
        ]))
        self.assertNotEqual(evidence, stalled_batch(calls, [
            {"id": "a", "result": "changed"}, {"id": "b", "result": "second"},
        ]))

    async def test_empty_freeze_reason_cannot_disable_safety_gate(self):
        item = await self.submit("queued")
        for reason in (None, "", "  ", False):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                await self.queue.freeze("s", "u", reason)
        self.assertEqual(await self.queue.list("s", "u"), [item])
        self.assertEqual((await self.queue.claim("s", "u", "follow_up"))["id"], item["id"])

    async def test_recover_checks_and_freezes_in_one_locked_transaction(self):
        active = await self.submit("active")
        await self.queue.claim("s", "u", "follow_up")
        with patch.object(self.queue, "list", AsyncMock(wraps=self.queue.list)) as unlocked_read:
            recovered = await self.queue.recover("s", "u")
        unlocked_read.assert_not_awaited()
        self.assertEqual([(row["id"], row["status"]) for row in recovered], [(active["id"], "blocked")])
        await self.queue.resume_reviewed("s", "u", True)
        self.assertIsNone(await self.queue.claim("s", "u", "follow_up"))
        with self.assertRaises(LookupError):
            await self.queue.recover("s", "other")

    async def test_concurrent_consumers_claim_each_input_once_in_kind_fifo(self):
        rows = [await self.submit(str(i), "steering" if i % 2 else "follow_up") for i in range(10)]
        for kind in ("follow_up", "steering"):
            consumers = [SessionInputQueue(self.factory) for _ in range(7)]
            claimed = await asyncio.wait_for(asyncio.gather(*(
                consumer.claim("s", "u", kind) for consumer in consumers
            )), 10)
            items = [item for item in claimed if item is not None]
            expected = [row for row in rows if row["kind"] == kind]
            self.assertEqual(sorted(item["sequence"] for item in items), [row["sequence"] for row in expected])
            self.assertEqual(len({item["id"] for item in items}), len(expected))
        self.assertTrue(all(row["status"] == "started" for row in await self.queue.list("s", "u")))

    async def test_ambiguous_tool_ids_cannot_trigger_two_round_no_progress_pause(self):
        call = {"id": "duplicate", "function": {"name": "read_file", "arguments": "{}"}}
        engine, session, model = self.engine([
            *(ChatResult(tool_calls=[call, dict(call)]) for _ in range(3)),
            ChatResult(content="done"),
        ])
        engine.tool_registry.register("read_file", "read", {"type": "object"}, lambda: "same")
        events = [event async for event in engine.run(session, "initial")]
        self.assertEqual(len(model.seen), 4)
        self.assertEqual(session.status.value, "completed")
        self.assertFalse(any(event.data.get("status") == "no_progress" for event in events))

    async def test_concurrent_conflicting_submissions_commit_one_payload(self):
        outcomes = await asyncio.wait_for(asyncio.gather(*(
            SessionInputQueue(self.factory).submit("s", "u", "same", "follow_up", message)
            for message in ("first", "second")
        ), return_exceptions=True), 10)
        self.assertEqual(sum(isinstance(value, ValueError) for value in outcomes), 1)
        successful = next(value for value in outcomes if isinstance(value, dict))
        self.assertEqual(await self.queue.list("s", "u"), [successful])
        self.assertEqual((await self.submit("next"))["sequence"], 2)

    async def test_freeze_submit_and_resume_races_preserve_unknown_effects(self):
        active = await self.submit("active")
        later = await self.submit("later")
        await self.queue.claim("s", "u", "follow_up")
        await asyncio.wait_for(asyncio.gather(
            self.queue.freeze("s", "u", "unknown effects"),
            SessionInputQueue(self.factory).submit("s", "u", "fresh", "follow_up", "fresh"),
        ), 10)
        self.assertTrue(all(row["status"] == "blocked" for row in await self.queue.list("s", "u")))
        await asyncio.wait_for(asyncio.gather(
            self.queue.resume_reviewed("s", "u", True),
            self.queue.finish("s", "u", active["id"], "completed"),
        ), 10)
        items = await self.queue.list("s", "u")
        self.assertEqual([row["status"] for row in items], ["blocked", "queued", "queued"])
        self.assertEqual(items[0]["error"], "unknown effects")
        self.assertEqual((await self.queue.claim("s", "u", "follow_up"))["id"], later["id"])

    async def test_completed_acknowledgements_are_idempotent_and_terminal(self):
        item = await self.submit("active")
        await self.queue.claim("s", "u", "follow_up")
        completed = await self.queue.finish("s", "u", item["id"], "completed")
        self.assertEqual(await self.queue.finish("s", "u", item["id"], "completed"), completed)
        self.assertEqual(await self.submit("active"), completed)
        with self.assertRaises(RuntimeError):
            await self.queue.finish("s", "u", item["id"], "failed", "late failure")
        self.assertEqual(await self.queue.recover("s", "u"), [])
        self.assertEqual(await self.queue.list("s", "u"), [completed])
