"""Private SQLite and scripted adapter; real FastAPI queue start routes."""

import asyncio
import json
import socket
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import uvicorn
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import chat, sessions
from app.core import ChatResult
from app.core.agent_engine import AgentEngine
from app.core.checkpoint import InMemoryCheckpointStore
from app.core.engine.input_queue import SessionInputQueue
from app.core.engine.run_storage import RunStorage
from app.storage import Base
from app.storage.database import (
    Agent,
    CheckpointRecord,
    Message,
    Session,
    SessionInput,
    Turn,
    UsageLog,
)
from app.storage.models_cost import CostRecord
from app.tools import ToolRegistry


class InputDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="input-dispatch-")
        self.db_engine = create_async_engine(
            "sqlite+aiosqlite:///" + str(Path(self.tmp.name) / "private.db")
        )
        self.factory = async_sessionmaker(self.db_engine, expire_on_commit=False)
        async with self.db_engine.begin() as conn:
            tables = [
                m.__table__
                for m in (
                    Agent,
                    Session,
                    SessionInput,
                    Turn,
                    Message,
                    UsageLog,
                    CostRecord,
                    CheckpointRecord,
                )
            ]
            await conn.run_sync(lambda db: Base.metadata.create_all(db, tables=tables))
        async with self.factory() as db:
            db.add(
                Agent(id="a", name="scripted", user_id="u", provider="ollama", model_id="scripted")
            )
            await db.flush()
            db.add(Session(id="s", agent_id="a", user_id="u", context_data={}))
            await db.commit()
        self.queue = SessionInputQueue(self.factory)
        self.model = SimpleNamespace(
            capabilities=SimpleNamespace(streaming=False, max_tokens=100000)
        )
        self.calls = []

        async def respond(messages, **kwargs):
            self.calls.append([dict(m) for m in messages])
            return ChatResult(content="answer " + str(len(self.calls)))

        self.model.chat = respond
        self.registry = SimpleNamespace(
            get_default=lambda: self.model, get_or_create=lambda **kwargs: self.model
        )
        self.patches = []
        for target, value in (
            ("app.storage.async_session", self.factory),
            ("app.core.ui_rules.refresh_rule_context", AsyncMock()),
            ("app.core.prompt_optimizer.maybe_optimize_instruction", AsyncMock()),
            ("app.core.agent_engine.AgentEngine._init_reasoning", Mock()),
            ("app.core.agent_engine.AgentEngine._init_sandbox", Mock()),
            ("app.core.agent_engine.AgentEngine._init_permissions", Mock()),
            ("app.api.v1.chat.async_session", self.factory),
            ("app.api.v1.sessions.async_session", self.factory),
            ("app.api.v1.chat._ChatModelRegistry", Mock(return_value=self.registry)),
        ):
            p = patch(target, value)
            p.start()
            self.patches.append(p)
        self.engine = AgentEngine(
            model_registry=self.registry,
            tool_registry=ToolRegistry(),
            checkpoint_store=InMemoryCheckpointStore(),
            run_store=RunStorage(self.factory),
        )
        self.engine.sandbox = self.engine.permission_overlay = self.engine.agent_mode = None
        self.engine._build_tools_for_session = Mock(return_value=[])
        for name in (
            "_set_agent_mode",
            "_send_start_notification",
            "_send_completion_notification",
            "_send_failure_notification",
            "_trigger_memory_reflection",
            "_record_profile_outcome",
            "_tick_evolution",
        ):
            setattr(self.engine, name, Mock())
        for name in (
            "_inject_memory_context",
            "_inject_core_memory",
            "_inject_profile_context",
            "_store_episodic_memory",
            "_archive_instruction",
        ):
            setattr(self.engine, name, AsyncMock())
        p = patch.object(chat, "get_engine", return_value=self.engine)
        p.start()
        self.patches.append(p)
        self.app = FastAPI()
        self.app.include_router(chat.router, prefix="/api/v1/sessions")
        self.app.include_router(sessions.router, prefix="/api/v1/sessions")
        self.app.dependency_overrides[chat.get_current_user] = lambda: "u"
        for router in (chat.router, sessions.router):
            for route in router.routes:
                for dependency in route.dependant.dependencies:
                    if dependency.name in {"_auth", "_scope_check"}:
                        self.app.dependency_overrides[dependency.call] = lambda: {}
        self.client = AsyncClient(transport=ASGITransport(app=self.app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        tasks = list(self.engine._background_tasks)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await self.db_engine.dispose()
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    async def submit(self, name, kind="follow_up"):
        return await self.queue.submit("s", "u", name, kind, name)

    def frames(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        frames = []
        for frame in response.text.strip().split("\n\n"):
            lines = frame.splitlines()
            frames.append((lines[0][7:], json.loads(lines[1][6:])))
        return frames

    async def test_cold_start_executes_fifo_and_reports_persisted_message_ids(self):
        first = await self.submit("first")
        second = await self.submit("second")
        async with self.factory() as db:
            db.add(Message(session_id="s", role="assistant", content="committed history"))
            await db.commit()
        with patch.object(
            chat.RecoveryManager,
            "restore_session",
            AsyncMock(side_effect=AssertionError("checkpoint replay")),
        ):
            frames = self.frames(await self.client.post("/api/v1/sessions/s/inputs/start"))
        self.assertEqual(
            [i["status"] for i in await self.queue.list("s", "u")], ["completed", "completed"]
        )
        turns = [data for name, data in frames if name == "turn_done"]
        self.assertEqual([t["input_id"] for t in turns], [first["id"], second["id"]])
        self.assertEqual(sum(name == "done" for name, _ in frames), 1)
        self.assertEqual(frames[-1][0], "done")
        self.assertFalse(any(name == "error" for name, _ in frames))
        self.assertTrue(any(m["content"] == "committed history" for m in self.calls[0]))
        self.assertEqual([m["content"] for m in self.calls[0] if m["role"] == "user"], ["first"])
        async with self.factory() as db:
            for turn in turns:
                message = await db.get(Message, turn["message_id"])
                self.assertEqual(message.role, "assistant")
                self.assertEqual((await db.get(Turn, turn["turn_id"])).status, "completed")
        reports = [data for name, data in frames if name == "runtime_report"]
        for report in reports:
            self.assertEqual(set(report), {"completed", "executing", "queued", "risks"})
            self.assertTrue(
                all(
                    isinstance(v, list) and all(isinstance(s, str) for s in v)
                    for v in report.values()
                )
            )
        print(
            "DISPATCH_EVIDENCE="
            + json.dumps(
                {"turn_done": turns, "report": reports[-1], "events": [name for name, _ in frames]}
            )
        )

    async def test_empty_or_steering_only_returns_409_without_start(self):
        for kind in (None, "steering"):
            if kind:
                await self.submit("steer", kind)
            response = await self.client.post("/api/v1/sessions/s/inputs/start")
            self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.calls, [])
        async with self.factory() as db:
            self.assertIsNone(await db.scalar(select(Turn)))

    async def test_bound_credential_is_not_persisted_or_streamed(self):
        await self.submit("safe")
        secret = "isolated-dispatch-credential-sentinel"
        with patch.object(chat, "decrypt_api_key", return_value=secret):
            response = await self.client.post("/api/v1/sessions/s/inputs/start")
        self.frames(response)
        chat._ChatModelRegistry.assert_called_with("ollama", "scripted", secret, None)
        self.assertNotIn(secret, response.text)
        async with self.factory() as db:
            for model in (Session, SessionInput, Turn, Message, CheckpointRecord):
                rows = (await db.scalars(select(model))).all()
                persisted = [
                    {
                        attribute.key: getattr(row, attribute.key)
                        for attribute in model.__mapper__.column_attrs
                    }
                    for row in rows
                ]
                self.assertNotIn(secret, repr(persisted))
        for checkpoint in self.engine._checkpoints._store.values():
            self.assertNotIn(secret, repr(checkpoint))

    async def test_frozen_and_unknown_started_inputs_are_never_executed(self):
        item = await self.submit("unknown")
        await self.queue.claim("s", "u", "follow_up")
        response = await self.client.post("/api/v1/sessions/s/inputs/start")
        self.assertEqual(response.status_code, 409, response.text)
        await self.queue.freeze("s", "u", "review required")
        response = await self.client.post("/api/v1/sessions/s/inputs/start")
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual((await self.queue.list("s", "u"))[0]["id"], item["id"])
        self.assertEqual(self.calls, [])

    async def test_reviewed_safe_queue_starts_new_turn_and_keeps_unknown_blocked(self):
        await self.submit("unknown")
        await self.queue.claim("s", "u", "follow_up")
        safe = await self.submit("safe")
        await self.queue.freeze("s", "u", "review required")
        await self.queue.resume_reviewed("s", "u", True)
        async with self.factory() as db:
            db.add(Turn(id="old", session_id="s", status="paused", completed_at=datetime.now()))
            await db.commit()
        frames = self.frames(await self.client.post("/api/v1/sessions/s/inputs/start"))
        turn = next(data for name, data in frames if name == "turn_done")
        self.assertEqual(turn["input_id"], safe["id"])
        self.assertNotEqual(turn["turn_id"], "old")
        self.assertEqual(
            [i["status"] for i in await self.queue.list("s", "u")], ["blocked", "completed"]
        )

    async def test_unfinished_turn_blocks_checkpoint_replay(self):
        await self.submit("safe")
        async with self.factory() as db:
            db.add(Turn(id="interrupted", session_id="s", status="running"))
            await db.commit()
        response = await self.client.post("/api/v1/sessions/s/inputs/start")
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.calls, [])
        self.assertEqual((await self.queue.list("s", "u"))[0]["status"], "queued")

    async def test_ownership_write_scope_and_credentials_fail_before_claim(self):
        await self.submit("safe")
        self.app.dependency_overrides[chat.get_current_user] = lambda: "other"
        self.assertEqual(
            (await self.client.post("/api/v1/sessions/s/inputs/start")).status_code, 404
        )
        self.app.dependency_overrides[chat.get_current_user] = lambda: "u"
        route = next(r for r in chat.router.routes if r.path.endswith("/inputs/start"))
        auth = next(d.call for d in route.dependant.dependencies if d.name == "_scope_check")

        def denied():
            raise HTTPException(403, "write required")

        self.app.dependency_overrides[auth] = denied
        self.assertEqual(
            (await self.client.post("/api/v1/sessions/s/inputs/start")).status_code, 403
        )
        self.app.dependency_overrides[auth] = lambda: {}
        with patch.object(chat, "_ChatModelRegistry", side_effect=ValueError("invalid credential")):
            self.assertEqual(
                (await self.client.post("/api/v1/sessions/s/inputs/start")).status_code, 422
            )
        self.assertEqual((await self.queue.list("s", "u"))[0]["status"], "queued")
        self.assertEqual(self.calls, [])

    async def test_reservation_during_preflight_returns_busy_before_claim(self):
        from app.core.engine.input_dispatch import prepare_dispatch

        await self.submit("safe")

        async def reserve(*args, **kwargs):
            result = await prepare_dispatch(*args, **kwargs)
            chat._chat_inflight.add("s")
            return result

        try:
            with patch("app.core.engine.input_dispatch.prepare_dispatch", side_effect=reserve):
                response = await self.client.post("/api/v1/sessions/s/inputs/start")
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual((await self.queue.list("s", "u"))[0]["status"], "queued")
            self.assertEqual(self.calls, [])
        finally:
            chat._chat_inflight.discard("s")

    async def test_real_sse_busy_and_disconnect_freezes_claimed_and_pending(self):
        await self.submit("active")
        await self.submit("later")
        entered = asyncio.Event()

        async def blocked(messages, **kwargs):
            entered.set()
            await asyncio.Event().wait()

        self.model.chat = blocked
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(self.app, lifespan="off", log_level="error"))
        task = asyncio.create_task(server.serve(sockets=[sock]))
        try:
            async with asyncio.timeout(10):
                while not server.started:
                    await asyncio.sleep(0.01)
            async with AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=10) as client:
                async with client.stream("POST", "/api/v1/sessions/s/inputs/start") as response:
                    self.assertEqual(response.status_code, 200)
                    await asyncio.wait_for(entered.wait(), 10)
                    self.assertEqual(
                        (await client.post("/api/v1/sessions/s/inputs/start")).status_code, 409
                    )
                    self.assertEqual(
                        (
                            await client.post("/api/v1/sessions/s/chat", json={"message": "busy"})
                        ).status_code,
                        409,
                    )
                async with asyncio.timeout(10):
                    while "s" in chat._chat_inflight:
                        await asyncio.sleep(0.01)
            self.assertEqual(
                [i["status"] for i in await self.queue.list("s", "u")], ["blocked", "blocked"]
            )
            self.assertNotIn("s", self.engine._session_locks)
            async with self.factory() as db:
                turn = await db.scalar(select(Turn))
                self.assertEqual(turn.status, "stopped")
                self.assertIsNotNone(turn.completed_at)
            print(
                "DISCONNECT_EVIDENCE="
                + json.dumps(
                    {
                        "inputs": ["blocked", "blocked"],
                        "turn_status": "stopped",
                        "lock_released": True,
                    }
                )
            )
        finally:
            server.should_exit = True
            await asyncio.wait_for(task, 10)
            sock.close()
