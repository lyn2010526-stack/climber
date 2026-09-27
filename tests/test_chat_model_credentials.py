"""Real routes, SQLite, crypto, session factory and registry; fake engine run/adapter.

Run with unittest discovery to avoid the shared-database pytest conftest.
No provider network traffic or real model credentials are used.
"""
# ruff: noqa: PT009, PT027

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import chat, model_discovery, router, sessions
from app.core import AgentEvent, AgentEventType
from app.core.agent_engine import AgentEngine
from app.core.api_key_crypto import encrypt_api_key
from app.core.auth import get_current_user
from app.core.principal import Principal, reset_current_principal, set_current_principal
from app.models.registry import PROVIDERS, ModelRegistry
from app.storage.database import Agent, ApiKey, Session


class FakeAdapter:
    def __init__(self, **kwargs):
        self.config = kwargs


class RecordingEngine(AgentEngine):
    """Only run/constructor are faked; session creation uses the real factory."""

    def __init__(self):
        self._sessions = {}
        self._session_locks = {}
        self.model_registry = ModelRegistry()
        self.created = []
        self.executed = []
        self.raise_stream = False

    def _init_reasoning(self):
        self.reasoning = SimpleNamespace(model_registry=self.model_registry)

    def create_session(self, **kwargs):
        self.created.append(kwargs)
        return super().create_session(**kwargs)

    async def run(self, session, _message):
        adapter = self.model_registry.get_or_create(
            session.provider, session.model_id, session.api_key, session.base_url,
        )
        self.executed.append((session.user_id, adapter, self.reasoning.model_registry.get_default()))
        if self.raise_stream:
            raise RuntimeError(f"upstream echoed {session.api_key}")
        yield AgentEvent(type=AgentEventType.TEXT, data={"content": "fake response"})


class ChatCredentialTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.database = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.addAsyncCleanup(self.database.dispose)
        tables = [Agent.__table__, ApiKey.__table__, Session.__table__]
        async with self.database.begin() as connection:
            await connection.run_sync(lambda conn: Agent.metadata.create_all(conn, tables=tables))
        self.db = async_sessionmaker(self.database, expire_on_commit=False)
        async with self.db() as db:
            db.add_all([
                Agent(id="agent-a", user_id="owner-a", name="A", provider="openai",
                      model_id="agent-model", api_key_encrypted=encrypt_api_key("agent-secret"),
                      base_url="https://agent.example/v1"),
                Agent(id="agent-b", user_id="owner-b", name="B", provider="openai",
                      model_id="agent-model", api_key_encrypted=encrypt_api_key("agent-b-secret")),
                ApiKey(id="key-a", user_id="owner-a", provider="openai", name="A",
                       api_key_encrypted=encrypt_api_key("selected-secret-a"),
                       base_url="https://selected.example/v1", is_active=True),
                ApiKey(id="key-b", user_id="owner-b", provider="openai", name="B",
                       api_key_encrypted=encrypt_api_key("selected-secret-b"), is_active=True),
            ])
            await db.commit()
        self.owner = "owner-a"
        self.engine = RecordingEngine()
        for target in (chat, sessions, model_discovery):
            patcher = patch.object(target, "async_session", self.db)
            patcher.start()
            self.addCleanup(patcher.stop)
        for patcher in [
            patch.object(chat, "get_engine", return_value=self.engine),
            patch.object(chat.RecoveryManager, "restore_session", new_callable=AsyncMock, return_value=False),
            patch.dict(PROVIDERS, {"openai": FakeAdapter}),
            patch.object(ModelRegistry, "_resolve_spec", side_effect=AssertionError("No environment fallback")),
        ]:
            patcher.start()
            self.addCleanup(patcher.stop)
        chat._chat_inflight.clear()
        self.addCleanup(chat._chat_inflight.clear)
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_current_user] = lambda: self.owner
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)

    async def create(self, credential="key-a", agent="agent-a", **overrides):
        settings = {"credential_id": credential, "provider": "openai", "model_id": "discovered-model"}
        settings.update(overrides)
        return await self.client.post("/api/v1/sessions", json={
            "agent_id": agent, "model_settings": settings,
        })

    async def send(self, session_id):
        return await self.client.post(f"/api/v1/sessions/{session_id}/chat", json={"message": "hello"})

    async def change_key(self, **values):
        async with self.db() as db:
            row = await db.get(ApiKey, "key-a")
            for name, value in values.items():
                setattr(row, name, value)
            await db.commit()

    async def test_discovery_route_is_registered(self):
        principal = set_current_principal(Principal(subject_id=self.owner))
        try:
            with patch.object(model_discovery, "discover_models", new_callable=AsyncMock) as discover:
                discover.return_value = {"provider": "openai", "source": "provider_api", "status": "empty", "models": []}
                response = await self.client.get("/api/v1/models/discover", params={"credential_id": "key-a"})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["credential_id"], "key-a")
        finally:
            reset_current_principal(principal)

    async def test_persist_and_execute_selected_credential_before_session_creation(self):
        response = await self.create(base_url="https://ignored.example", api_key="ignored-client-key")
        self.assertEqual(response.status_code, 200, response.text)
        sid = response.json()["id"]
        async with self.db() as db:
            row = await db.get(Session, sid)
            self.assertEqual(row.model_settings, {
                "credential_id": "key-a", "provider": "openai", "model_id": "discovered-model",
            })
        reply = await self.send(sid)
        self.assertEqual(reply.status_code, 200, reply.text)
        self.assertIn("fake response", reply.text)
        self.assertEqual(self.engine.created[0]["api_key"], "selected-secret-a")
        adapter = self.engine.executed[-1][1]
        self.assertEqual(adapter.config["api_key"], "selected-secret-a")
        self.assertEqual(adapter.config["base_url"], "https://selected.example/v1")
        self.assertIs(adapter, self.engine.executed[-1][2])

    async def test_default_preserves_agent_model_and_key(self):
        created = await self.client.post("/api/v1/sessions", json={"agent_id": "agent-a"})
        self.assertEqual(created.json()["model_id"], "agent-model")
        response = await self.send(created.json()["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.engine.executed[-1][1].config["api_key"], "agent-secret")

    async def test_all_create_paths_persist_credential(self):
        for suffix in ("", "/", "/create"):
            response = await self.client.post(f"/api/v1/sessions{suffix}", json={
                "model_settings": {"credential_id": "key-a", "model_id": "chosen"},
            })
            self.assertEqual(response.status_code, 200, response.text)
            async with self.db() as db:
                row = await db.get(Session, response.json()["id"])
                self.assertEqual(row.model_settings["credential_id"], "key-a")

    async def test_reject_other_owner_credential_and_agent(self):
        self.assertEqual((await self.create(credential="key-b")).status_code, 404)
        self.assertEqual((await self.create(agent="agent-b")).status_code, 404)
        self.assertEqual(self.engine.created, [])

    async def test_reject_invalid_settings_and_provider_mismatch(self):
        for settings in ({"credential_id": ""}, {"credential_id": 3}, {"model_id": []},
                         {"credential_id": "key-a"},
                         {"credential_id": "key-a", "model_id": "m", "provider": "anthropic"}):
            response = await self.client.post("/api/v1/sessions", json={"model_settings": settings})
            self.assertEqual(response.status_code, 422, response.text)

    async def test_revoked_key_rejected_for_creation_cold_and_warm_chat(self):
        cold = (await self.create()).json()["id"]
        warm = (await self.create()).json()["id"]
        await self.send(warm)
        await self.change_key(is_active=False)
        self.assertEqual((await self.create()).status_code, 404)
        for sid in (cold, warm):
            response = await self.send(sid)
            self.assertEqual(response.status_code, 404, response.text)
            self.assertIn("revoked", response.text)
        self.assertEqual(len(self.engine.executed), 1)

    async def test_deleted_key_rejected_for_warm_chat(self):
        sid = (await self.create()).json()["id"]
        await self.send(sid)
        async with self.db() as db:
            await db.delete(await db.get(ApiKey, "key-a"))
            await db.commit()
        self.assertEqual((await self.send(sid)).status_code, 404)
        self.assertEqual(len(self.engine.executed), 1)

    async def test_key_owner_change_rejected_for_warm_chat(self):
        sid = (await self.create()).json()["id"]
        await self.send(sid)
        await self.change_key(user_id="owner-b")
        self.assertEqual((await self.send(sid)).status_code, 404)

    async def test_session_owner_checked_again_for_cached_session(self):
        sid = (await self.create()).json()["id"]
        await self.send(sid)
        self.owner = "owner-b"
        self.assertEqual((await self.send(sid)).status_code, 404)
        self.assertEqual(len(self.engine.executed), 1)

    async def test_missing_and_unreadable_keys_do_not_fall_back(self):
        sid = (await self.create()).json()["id"]
        for encrypted in ("", "enc:v1:broken"):
            await self.change_key(api_key_encrypted=encrypted)
            response = await self.send(sid)
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.engine.created, [])
        self.assertEqual(self.engine.executed, [])

    async def test_rotation_rebinds_warm_session_and_ignores_global_cache(self):
        self.engine.model_registry.register_model("discovered-model", "openai", "poisoned-global-key")
        sid = (await self.create()).json()["id"]
        await self.send(sid)
        await self.change_key(api_key_encrypted=encrypt_api_key("rotated-secret"), base_url="https://rotated.example/v1")
        await self.send(sid)
        self.assertEqual(len(self.engine.created), 1)
        self.assertIsNot(self.engine.executed[0][1], self.engine.executed[1][1])
        self.assertEqual(self.engine.executed[-1][1].config["api_key"], "rotated-secret")
        self.assertEqual(self.engine._sessions[sid].session_config.api_key, "rotated-secret")
        self.assertEqual(self.engine.executed[-1][1].config["base_url"], "https://rotated.example/v1")
        self.assertEqual(self.engine.model_registry.get_model("openai", "discovered-model").config["api_key"], "poisoned-global-key")

    async def test_two_owners_same_model_receive_distinct_adapters(self):
        sid_a = (await self.create()).json()["id"]
        await self.send(sid_a)
        self.owner = "owner-b"
        sid_b = (await self.create(credential="key-b", agent="agent-b")).json()["id"]
        await self.send(sid_b)
        first, second = self.engine.executed
        self.assertIsNot(first[1], second[1])
        self.assertEqual(first[1].config["api_key"], "selected-secret-a")
        self.assertEqual(second[1].config["api_key"], "selected-secret-b")

    async def test_registry_default_is_bound_and_alternate_spec_fails(self):
        registry = chat._ChatModelRegistry("openai", "chosen", "test-secret", None)
        self.assertIs(registry.get_or_create("openai:chosen"), registry.get_default())
        with self.assertRaises(ValueError):
            registry.get_or_create("anthropic:another")

    async def test_stream_errors_are_redacted_and_release_busy_guard(self):
        sid = (await self.create()).json()["id"]
        self.engine.raise_stream = True
        response = await self.send(sid)
        self.assertIn("Model execution failed", response.text)
        self.assertNotIn("selected-secret-a", response.text)
        self.assertNotIn(sid, chat._chat_inflight)

    async def test_busy_request_is_rejected_without_mutating_session(self):
        sid = (await self.create()).json()["id"]
        chat._chat_inflight.add(sid)
        response = await self.send(sid)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.engine.created, [])

    async def test_failed_recovery_cannot_leave_a_partially_restored_session(self):
        sid = (await self.create()).json()["id"]
        with patch.object(chat.RecoveryManager, "restore_session", side_effect=ValueError("pending writes")), \
                self.assertRaises(ValueError):
            await self.send(sid)
        self.assertNotIn(sid, self.engine._sessions)
        self.assertNotIn(sid, chat._chat_inflight)
        self.assertEqual((await self.send(sid)).status_code, 200)
