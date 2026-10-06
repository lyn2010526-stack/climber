"""Backend reliability: durable audit log for login/permission/file/agent events."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.engine.validation import validate_tool_call
from app.core.observability.audit_store import DurableAuditStore
from app.core.permission_rules import PermissionConfig, PermissionTier
from app.main import app
from app.storage import Base
from app.storage.database import Session
from app.storage.models_memory import AuditLog


class AuditStoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="audit-store-")
        self.addCleanup(self.tmp.cleanup)
        self.db_engine = create_async_engine("sqlite+aiosqlite:///" + str(Path(self.tmp.name) / "audit.db"))
        self.addAsyncCleanup(self.db_engine.dispose)
        self.factory = async_sessionmaker(self.db_engine, expire_on_commit=False)
        async with self.db_engine.begin() as conn:
            await conn.run_sync(lambda db: Base.metadata.create_all(
                db, tables=[AuditLog.__table__, Session.__table__]))
        self.store = DurableAuditStore(self.factory)

    async def test_login_success_and_failure(self):
        self.assertTrue(await self.store.log_login(user_id="42", username="alice", success=True))
        self.assertTrue(await self.store.log_login(username="alice", success=False, reason="bad password"))
        entries = await self.store.list_events()
        self.assertEqual(len(entries), 2)
        success = next(e for e in entries if e["result"] == "granted")
        self.assertEqual(success["action"], "auth:login")
        self.assertEqual(success["severity"], "info")
        self.assertEqual(success["user_id"], "42")
        self.assertTrue(success["details"]["success"])
        failure = next(e for e in entries if e["result"] == "denied")
        self.assertEqual(failure["severity"], "warning")
        self.assertEqual(failure["details"]["reason"], "bad password")

    async def test_permission_file_and_agent_events(self):
        await self.store.log_permission_decision(
            session_id="s1", user_id="u1", tool_name="write_file", allowed=False, reason="read-only tier")
        await self.store.log_file_change(
            session_id="s1", user_id="u1", operation="write", path="/tmp/a.py", details={"bytes": 12})
        await self.store.log_agent_action(
            session_id="s1", user_id="u1", action="run_started", details={"turn_id": "t1"})
        self.assertEqual(await self.store.count_events(), 3)
        entry = (await self.store.list_events(action="permission:decision"))[0]
        self.assertEqual(entry["details"]["allowed"], False)
        file_events = await self.store.list_events(action="file:write")
        self.assertEqual(len(file_events), 1)
        self.assertEqual(file_events[0]["severity"], "critical")
        agent_events = await self.store.list_events(action="agent:run_started")
        self.assertEqual(agent_events[0]["details"]["turn_id"], "t1")
        info_events = await self.store.list_events(session_id="s1", severity="info")
        self.assertEqual(len(info_events), 1)
        self.assertEqual(info_events[0]["action"], "agent:run_started")
        permission_events = await self.store.list_events(session_id="s1", severity="warning")
        self.assertEqual(len(permission_events), 1)
        self.assertEqual(permission_events[0]["action"], "permission:decision")

    async def test_count_events_filters(self):
        await self.store.log_login(user_id="7", username="bob", success=True)
        await self.store.log_agent_action(session_id="s1", action="run_started")
        self.assertEqual(await self.store.count_events(user_id="7"), 1)
        self.assertEqual(await self.store.count_events(session_id="s1"), 1)
        self.assertEqual(await self.store.count_events(action="auth:login"), 1)

    async def test_missing_table_fails_open(self):
        tmp = tempfile.TemporaryDirectory(prefix="audit-nosan-")
        self.addCleanup(tmp.cleanup)
        engine = create_async_engine("sqlite+aiosqlite:///" + str(Path(tmp.name) / "empty.db"))
        self.addAsyncCleanup(engine.dispose)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(lambda db: Base.metadata.create_all(db, tables=[Session.__table__]))
        store = DurableAuditStore(factory)
        self.assertFalse(await store.log_login(user_id="1", username="x", success=True))
        self.assertEqual(await store.list_events(), [])
        self.assertEqual(await store.count_events(), 0)


class _Session:
    agent_id = "agent"
    user_id = "user"
    session_id = "session-1"
    _approved_tool_calls: set[str] = set()

    def __init__(self, config: PermissionConfig) -> None:
        self.permission_config = config


class PermissionMirrorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="audit-mirror-")
        self.addCleanup(self.tmp.cleanup)
        self.db_engine = create_async_engine("sqlite+aiosqlite:///" + str(Path(self.tmp.name) / "mirror.db"))
        self.addAsyncCleanup(self.db_engine.dispose)
        self.factory = async_sessionmaker(self.db_engine, expire_on_commit=False)
        async with self.db_engine.begin() as conn:
            await conn.run_sync(lambda db: Base.metadata.create_all(db, tables=[AuditLog.__table__]))
        self.store = DurableAuditStore(self.factory)

    async def test_permission_decision_mirrors_durably(self):
        config = PermissionConfig(tier=PermissionTier.READ_ONLY)
        with patch("app.core.observability.audit_store.audit_log", self.store):
            allowed, _ = validate_tool_call(_Session(config), "write_file", {"path": "a.py", "content": "x"})
            self.assertFalse(allowed)
            for _ in range(40):
                if await self.store.count_events(action="permission:decision"):
                    break
                await asyncio.sleep(0.05)
        entries = await self.store.list_events(action="permission:decision")
        self.assertTrue(entries)
        self.assertEqual(entries[0]["details"]["allowed"], False)
        self.assertEqual(entries[0]["details"]["tool"], "write_file")
        self.assertEqual(entries[0]["session_id"], "session-1")


class AuditLogEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_audit_log_endpoint_returns_persisted_events(self):
        from app.core.observability.audit_store import audit_log

        await audit_log.log_login(user_id="9", username="carol", success=True)
        await audit_log.log_agent_action(session_id="session-9", action="run_started")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/observability/audit-log")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertGreaterEqual(payload["total"], 2)
            actions = {entry["action"] for entry in payload["entries"]}
            self.assertIn("auth:login", actions)
            self.assertIn("agent:run_started", actions)
            filtered = await client.get("/api/v1/observability/audit-log", params={"severity": "info"})
            self.assertEqual(filtered.status_code, 200)
            self.assertGreaterEqual(filtered.json()["total"], 1)