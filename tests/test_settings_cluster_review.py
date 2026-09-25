"""Standalone unittest regressions; no main app or shared pytest fixtures."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.services import settings_service
from app.storage import Base, get_db
from app.storage.models_groups import AgentGroup, AgentGroupMember
from app.storage.models_platform import UserSettings


def load_route(name: str, path: str):
    # Load only the tested routers, avoiding the full API aggregation import.
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


settings_route = load_route("review_settings_route", "app/api/v1/settings.py")
groups_route = load_route("review_groups_route", "app/api/v1/routes/groups.py")


class SettingsClusterReviewTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temp = tempfile.TemporaryDirectory(prefix="settings-cluster-", dir="/tmp/opencode")
        self.addCleanup(temp.cleanup)
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{temp.name}/review.db")
        self.addAsyncCleanup(self.engine.dispose)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda conn: Base.metadata.create_all(
                conn, tables=[UserSettings.__table__, AgentGroup.__table__, AgentGroupMember.__table__]
            ))
        for target, attr, value in [
            (settings_service, "async_session", self.sessions),
            (groups_route, "async_session", self.sessions),
            (settings, "enable_auth", True),
        ]:
            patcher = patch.object(target, attr, value)
            patcher.start()
            self.addCleanup(patcher.stop)

        app = FastAPI()

        @app.middleware("http")
        async def test_identity(request: Request, call_next):
            owner = request.headers.get("x-test-owner")
            if owner:
                request.state.auth = {
                    "owner": owner,
                    "method": "api_key",
                    "scopes": request.headers.get("x-test-scopes", "read write").split(),
                }
            return await call_next(request)

        async def test_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = test_db
        app.include_router(settings_route.router, prefix="/settings")
        app.include_router(groups_route.router)
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)
        self.owner = {"x-test-owner": "alice"}

    async def test_persisted_round_trip_and_owner_isolation(self):
        response = await self.client.patch("/settings/", headers=self.owner, json={
            "autonomous_agent_mode": True, "token_throttle_mcp_enabled": True,
        })
        self.assertEqual(response.status_code, 200, response.text)
        await self.engine.dispose()
        saved = await self.client.get("/settings/", headers=self.owner)
        self.assertTrue(saved.json()["autonomous_agent_mode"])
        self.assertTrue(saved.json()["token_throttle_mcp_enabled"])
        other = await self.client.get("/settings/", headers={"x-test-owner": "bob"})
        self.assertFalse(other.json()["autonomous_agent_mode"])
        self.assertFalse(other.json()["token_throttle_mcp_enabled"])
        response = await self.client.patch("/settings/", headers=self.owner, json={
            "autonomous_agent_mode": False,
        })
        self.assertEqual(response.status_code, 200)
        saved = await self.client.get("/settings/", headers=self.owner)
        self.assertFalse(saved.json()["autonomous_agent_mode"])
        self.assertTrue(saved.json()["token_throttle_mcp_enabled"])
        async with self.sessions() as db:
            rows = (await db.execute(select(UserSettings))).scalars().all()
            self.assertEqual({row.user_id for row in rows}, {"alice", "bob"})

    async def test_unsupported_notifications_rejected_atomically(self):
        for data in [
            {"notifications": {"email_task_done": True, "webhook_url": "https://example.com/hook"}},
            {"autonomous_agent_mode": True, "notifications": {"webhook_task_failed": True}},
            {"autonomous_agent_mode": True, "profile": {"email": "test@example.com"}},
            {"autonomous_agent_mode": True, "user_id": "bob"},
        ]:
            with self.subTest(data=data):
                response = await self.client.patch("/settings/", headers=self.owner, json=data)
                self.assertEqual(response.status_code, 422, response.text)
                self.assertIn("未保存", response.json()["detail"])
        async with self.sessions() as db:
            self.assertEqual((await db.execute(select(UserSettings))).scalars().all(), [])

    async def test_invalid_boolean_values_are_rejected(self):
        for value in ["false", 0, 1, None, [], {}]:
            with self.subTest(value=value):
                response = await self.client.patch("/settings/", headers=self.owner, json={
                    "autonomous_agent_mode": value,
                })
                self.assertEqual(response.status_code, 422, response.text)

    async def test_empty_update_is_rejected(self):
        response = await self.client.patch("/settings/", headers=self.owner, json={})
        self.assertEqual(response.status_code, 400)

    async def test_missing_identity_is_rejected(self):
        response = await self.client.get("/settings/")
        self.assertEqual(response.status_code, 401)

    async def test_read_scope_cannot_update(self):
        response = await self.client.patch("/settings/", headers={
            **self.owner, "x-test-scopes": "read",
        }, json={"autonomous_agent_mode": True})
        self.assertEqual(response.status_code, 403, response.text)

    async def test_group_detail_returns_only_owned_real_members(self):
        async with self.sessions() as db:
            db.add_all([
                AgentGroup(id="alice-group", name="Alice", user_id="alice"),
                AgentGroup(id="bob-group", name="Bob", user_id="bob"),
            ])
            await db.flush()
            db.add(AgentGroupMember(id="member-a", group_id="alice-group", agent_id="agent-a", role="planner"))
            await db.commit()
        response = await self.client.get("/groups/alice-group", headers=self.owner)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([m["id"] for m in response.json()["members"]], ["member-a"])
        hidden = await self.client.get("/groups/alice-group", headers={"x-test-owner": "bob"})
        self.assertEqual(hidden.status_code, 404)
        missing = await self.client.get("/groups/missing", headers=self.owner)
        self.assertEqual(missing.status_code, 404)
        empty = await self.client.get("/groups/bob-group", headers={"x-test-owner": "bob"})
        self.assertEqual(empty.json()["members"], [])


if __name__ == "__main__":
    unittest.main()
