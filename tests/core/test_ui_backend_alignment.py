"""Offline ASGI/SQLite contracts. Identity and task execution are scripted doubles.

Run with --noconftest to keep shared database cleanup out of this suite.
"""

import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings

with patch.object(settings, "database_url", "sqlite+aiosqlite:///:memory:"):
    from app.api.v1 import ui_rules
    from app.api.v1.routes import groups, skills, tasks
    from app.core import task_worker
    from app.core import ui_rules as rules
    from app.core.agent_engine import AgentEngine
    from app.core.principal import (
        get_context_principal,
        get_current_principal,
        principal_from_auth,
        reset_current_principal,
        set_current_principal,
    )
    from app.storage.database import Document
    from app.storage.models_groups import AgentGroup
    from app.storage.models_platform import AutoLoopTask, Skill


class AlignmentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.addAsyncCleanup(engine.dispose)
        self.sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Document.__table__.create)
            await connection.run_sync(AutoLoopTask.__table__.create)
            await connection.run_sync(AgentGroup.__table__.create)
            await connection.run_sync(Skill.__table__.create)
        self.enterContext(patch.object(rules, "async_session", self.sessions))
        self.enterContext(patch.object(task_worker, "async_session", self.sessions))
        self.enterContext(patch.object(groups, "async_session", self.sessions))
        self.enterContext(patch.object(skills, "async_session", self.sessions))
        self.enterContext(patch.object(settings, "enable_auth", True))
        self.manager = task_worker.TaskManager(max_task_retries=1)
        self.enterContext(patch.object(tasks, "task_manager", self.manager))
        app = FastAPI()
        app.include_router(ui_rules.router, prefix="/api/v1")
        app.include_router(tasks.router, prefix="/api/v1")
        app.include_router(groups.router, prefix="/api/v1")
        app.include_router(skills.router, prefix="/api/v1")
        app.dependency_overrides[get_current_principal] = get_context_principal
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )
        self.addAsyncCleanup(self.client.aclose)

    async def request(self, method, path, user="alice", scopes=("read", "write"), **kwargs):
        token = set_current_principal(principal_from_auth({"id": user, "scopes": scopes}))
        try:
            return await self.client.request(method, "/api/v1" + path, **kwargs)
        finally:
            reset_current_principal(token)

    async def seed_task(self, status="running"):
        async with self.sessions() as db:
            db.add(AutoLoopTask(id="t", owner_id="alice", objective="task", status=status))
            await db.commit()

    async def test_rules_persist_and_refresh_without_promoting_policy(self):
        for kind in rules.RULE_KINDS:
            response = await self.request("PUT", f"/ui/rules/{kind}", json={"content": kind})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["effective"], "next_iteration")
        response = await self.request("GET", "/ui/rules")
        self.assertEqual([r["content"] for r in response.json()], list(rules.RULE_KINDS))
        session = SimpleNamespace(
            user_id="alice",
            messages=[
                {"role": "system", "content": "policy"},
                {"role": "user", "content": "go"},
            ],
        )
        await rules.refresh_rule_context(session)
        await rules.refresh_rule_context(session)
        self.assertEqual(len(session.messages), 3)
        self.assertEqual(session.messages[0]["content"], "policy")
        self.assertEqual(session.messages[1]["role"], "user")
        self.assertIn("[project]\nproject", session.messages[1]["content"])
        other = await self.request("GET", "/ui/rules", user="bob")
        self.assertTrue(all(r["content"] == "" for r in other.json()))
        session.user_id = "bob"
        await rules.refresh_rule_context(session)
        self.assertEqual(len(session.messages), 2)

    async def test_rules_conflict_validation_and_read_scope(self):
        first = await self.request("PUT", "/ui/rules/soul", json={"content": "v1"})
        self.assertEqual(first.status_code, 200)
        stale = await self.request("PUT", "/ui/rules/soul", json={"content": "stale"})
        self.assertEqual(stale.status_code, 409)
        revision = first.json()["revision"]
        update = await self.request(
            "PUT",
            "/ui/rules/soul",
            json={"content": "v2", "revision": revision},
        )
        self.assertEqual(update.status_code, 200)
        stale = await self.request(
            "PUT",
            "/ui/rules/soul",
            json={"content": "v3", "revision": revision},
        )
        self.assertEqual(stale.status_code, 409)
        readonly = await self.request(
            "PUT",
            "/ui/rules/soul",
            scopes=("read",),
            json={"content": "x"},
        )
        self.assertEqual(readonly.status_code, 403)
        for path, body in [
            ("unknown", {"content": "x"}),
            ("soul", {"content": "x", "owner_id": "bob"}),
            ("soul", {"content": "x" * 32001}),
        ]:
            response = await self.request("PUT", f"/ui/rules/{path}", json=body)
            self.assertEqual(response.status_code, 422)

    async def test_snapshot_owner_history_and_terminal_sse(self):
        await self.seed_task("completed")
        await self.manager._emit_progress("t", {"status": "completed"})
        response = await self.request("GET", "/tasks/t/snapshot")
        self.assertEqual(response.status_code, 200, response.text)
        snapshot = response.json()
        self.assertEqual(snapshot["data"]["status"], "completed")
        self.assertEqual(snapshot["events"][0]["type"], "task_update")
        self.assertEqual(snapshot["sequence"], snapshot["events"][0]["sequence"])
        for path in ("snapshot", "events"):
            other = await self.request("GET", f"/tasks/t/{path}", user="bob")
            self.assertEqual(other.status_code, 404)
        stream = await self.request("GET", "/tasks/t/events")
        frame = json.loads(stream.text.removeprefix("data: ").strip())
        self.assertEqual(frame["type"], "snapshot")
        self.assertFalse(self.manager._event_subscribers)
        self.manager._event_history.clear()
        restart = await self.request("GET", "/tasks/t/snapshot")
        self.assertEqual(restart.json()["data"]["status"], "completed")
        self.assertEqual(restart.json()["events"], [])

    async def test_sse_heartbeat_keeps_subscription_alive_and_cleans_up(self):
        await self.seed_task()
        response = await tasks.task_events("t", {"id": "alice"})
        stream = response.body_iterator
        self.assertIn('"snapshot"', await anext(stream))

        async def idle(awaitable, timeout):
            awaitable.close()
            raise TimeoutError

        with patch.object(tasks.asyncio, "wait_for", idle):
            self.assertEqual(await anext(stream), ": keep-alive\n\n")
            self.assertEqual(await anext(stream), ": keep-alive\n\n")
        await self.manager._emit_progress("t", {"status": "failed", "error": "real failure"})
        self.assertIn('"failed"', await anext(stream))
        with self.assertRaises(StopAsyncIteration):
            await anext(stream)
        self.assertFalse(self.manager._event_subscribers)

    async def test_event_history_is_bounded_and_monotonic(self):
        for i in range(105):
            await self.manager.emit_event("t", "progress", {"step": i})
        history = list(self.manager._event_history["t"])
        self.assertEqual(len(history), 100)
        self.assertEqual(history[0]["sequence"], 6)
        self.assertEqual(history[-1]["sequence"], 105)

    async def test_retry_failed_result_stays_failed(self):
        await self.seed_task()
        handler = AsyncMock(return_value={"status": "failed", "error": "scripted failure"})
        await self.manager._retry_or_fail(
            "t",
            "test",
            "alice",
            {},
            handler,
            "error",
            RuntimeError(),
        )
        state = await self.manager.get_status("t", "alice")
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["error"], "scripted failure")
        self.assertEqual(self.manager._event_history["t"][-1]["data"]["status"], "failed")
        response = await self.request("GET", "/tasks/")
        self.assertEqual(response.json()[0]["error"], "scripted failure")
        self.assertIsNotNone(response.json()[0]["finished_at"])

    async def test_approval_resolution_preserves_owner(self):
        session = SimpleNamespace(
            user_id="alice",
            _pending_permission={"tool_call_id": "call"},
            _permission_event=asyncio.Event(),
        )
        engine = SimpleNamespace(_sessions={"s": session})
        self.assertFalse(AgentEngine.resolve_permission(engine, "call", "allow", owner_id="bob"))
        self.assertFalse(session._permission_event.is_set())
        self.assertTrue(AgentEngine.resolve_permission(engine, "call", "deny", owner_id="alice"))
        self.assertEqual(session._pending_permission["decision"], "deny")

    async def test_group_snapshot_owner_contract(self):
        async with self.sessions() as db:
            db.add(AgentGroup(id="g", user_id="alice", name="group"))
            await db.commit()
        response = await self.request("GET", "/groups/g/snapshot")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["group_id"], "g")
        self.assertEqual(response.json()["history_scope"], "process_recent")
        self.assertIn("task_tree", response.json())
        other = await self.request("GET", "/groups/g/snapshot", user="bob")
        self.assertEqual(other.status_code, 404)

    async def test_skill_switch_persists_for_owner_and_requires_write(self):
        async with self.sessions() as db:
            db.add(Skill(id="skill", user_id="alice", name="scripted skill", is_enabled=True))
            await db.commit()
        response = await self.request("POST", "/skills/skill/disable")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["is_enabled"])
        listed = await self.request("GET", "/skills")
        self.assertFalse(listed.json()[0]["is_enabled"])
        other = await self.request("POST", "/skills/skill/enable", user="bob")
        self.assertEqual(other.status_code, 404)
        readonly = await self.request("POST", "/skills/skill/enable", scopes=("read",))
        self.assertEqual(readonly.status_code, 403)
        response = await self.request("POST", "/skills/skill/enable")
        self.assertTrue(response.json()["is_enabled"])
