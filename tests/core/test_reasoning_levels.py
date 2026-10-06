"""Thinking-level API and level-to-model-parameters plumbing.

Mirrors ``tests/core/test_slash_commands.py``: real router mounted on a bare
FastAPI app over in-memory SQLite, so the module runs without the shared
conftest or the app.main import chain (which hard-exits without playwright).
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.routes import reasoning as reasoning_module
from app.api.v1.routes.reasoning import (
    DEFAULT_REASONING_LEVEL,
    LEVEL_PARAMS,
    LevelAwareModelRegistry,
    REASONING_LEVELS,
    level_from_context,
    level_params,
)
from app.core import AgentEventType, ChatResult
from app.core.agent_engine import AgentEngine
from app.core.engine.run_storage import RunStorage
from app.core.session import AgentSession, SessionConfig
from app.storage import Base
from app.storage.database import Session as SessionModel


class LevelMappingTests(unittest.TestCase):
    def test_three_levels_have_distinct_parameters(self):
        rows = [level_params(level) for level in REASONING_LEVELS]
        for key in ("max_tokens", "temperature", "reasoning_effort"):
            values = [row[key] for row in rows]
            self.assertEqual(len(set(values)), len(values), f"{key} must differ per level")

    def test_default_level_is_listed(self):
        self.assertIn(DEFAULT_REASONING_LEVEL, REASONING_LEVELS)

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            level_params("ultra")

    def test_level_from_context_falls_back_to_default(self):
        self.assertEqual(level_from_context({}), DEFAULT_REASONING_LEVEL)
        self.assertEqual(level_from_context({"reasoning_level": "high"}), "high")
        self.assertEqual(level_from_context({"reasoning_level": "warp"}), DEFAULT_REASONING_LEVEL)
        self.assertEqual(level_from_context(None), DEFAULT_REASONING_LEVEL)


class ScriptedAdapter:
    """Records every call's kwargs; streams one text chunk then stops."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.capabilities = SimpleNamespace(streaming=True, max_tokens=100000)

    async def stream_chat(self, messages, tools=None, **kwargs):
        self.calls.append({"messages": messages, "tools": tools, **kwargs})
        yield ChatResult(content="done", finish_reason="stop")

    async def chat(self, messages, tools=None, **kwargs):
        self.calls.append({"messages": messages, "tools": tools, **kwargs})
        return ChatResult(content="done", finish_reason="stop")


def make_session(context_data=None):
    return AgentSession(SessionConfig(
        session_id="s-1", agent_id="", user_id="u-1",
        provider="scripted", model_id="fake-model",
    ), context=context_data)


class LevelAffectsModelCallTests(unittest.IsolatedAsyncioTestCase):
    """Run the real engine loop with the level-aware registry and assert the
    parameters the scripted model client actually received."""

    async def asyncSetUp(self):
        # RunStorage(None) falls back to ``app.storage.async_session``; give it
        # a real factory over an in-memory database (same pattern as the
        # isolated engine audit tests) so ``run`` performs its bookkeeping
        # without touching the developer database.
        import tempfile
        from pathlib import Path

        import sqlalchemy
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from app.storage import Base
        from app.storage.database import (
            Agent,
            CheckpointRecord,
            Message,
            Session as SessionRow,
            SessionInput,
            Turn,
            UsageLog,
        )
        from app.storage.models_cost import CostRecord

        tmp = tempfile.TemporaryDirectory(prefix="reasoning-levels-")
        self.addAsyncCleanup(tmp.cleanup)
        self.db_engine = create_async_engine(
            "sqlite+aiosqlite:///" + str(Path(tmp.name) / "isolated.db"),
        )

        @sqlalchemy.event.listens_for(self.db_engine.sync_engine, "connect")
        def _fk(connection, record):  # pragma: no cover - pragma boilerplate
            connection.execute("PRAGMA foreign_keys=ON")

        self.factory = async_sessionmaker(self.db_engine, expire_on_commit=False)
        tables = [
            model.__table__
            for model in (
                Agent,
                SessionRow,
                SessionInput,
                Turn,
                Message,
                UsageLog,
                CheckpointRecord,
                CostRecord,
            )
        ]
        async with self.db_engine.begin() as connection:
            await connection.run_sync(lambda conn: Base.metadata.create_all(conn, tables=tables))
        self.addAsyncCleanup(self.db_engine.dispose)
        self.patches = [
            patch("app.storage.async_session", self.factory),
            patch("app.storage.engine", self.db_engine),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    async def _run_turn(self, level: str) -> list[dict]:
        adapter = ScriptedAdapter()
        base_registry = SimpleNamespace(
            get_or_create=lambda *args, **kwargs: adapter,
            get_default=lambda: adapter,
        )
        engine = AgentEngine(
            model_registry=LevelAwareModelRegistry(base_registry, level_params(level)),
            tool_registry=SimpleNamespace(),
            run_store=RunStorage(self.factory),
        )
        # The turn's model-call path is what matters here; storage, sandbox and
        # notification side effects are stubbed like the runtime audit tests do.
        for name in (
            "_save_checkpoint", "_set_agent_mode", "_send_start_notification",
            "_send_completion_notification", "_send_failure_notification",
            "_trigger_memory_reflection",
        ):
            setattr(engine, name, AsyncMock(return_value=None))
        for name in (
            "_inject_memory_context", "_inject_core_memory", "_store_episodic_memory",
        ):
            setattr(engine, name, AsyncMock(return_value=None))
        engine.sandbox = None
        engine.permission_overlay = None
        engine.agent_mode = None
        with patch("app.core.agent_engine.persist_message", new_callable=AsyncMock, return_value="m-1"):
            session = make_session()
            async for _event in engine.run(session, "hello"):
                pass
        self.assertEqual(adapter.calls, adapter.calls)
        self.assertTrue(adapter.calls, "the engine never called the model")
        return adapter.calls

    async def test_low_and_high_send_different_parameters(self):
        low_calls = await self._run_turn("low")
        high_calls = await self._run_turn("high")
        low, high = low_calls[0], high_calls[0]
        for key, value in LEVEL_PARAMS["low"].items():
            self.assertEqual(low[key], value, f"low turn missing {key}={value}")
        for key, value in LEVEL_PARAMS["high"].items():
            self.assertEqual(high[key], value, f"high turn missing {key}={value}")
        self.assertNotEqual(
            {k: low[k] for k in LEVEL_PARAMS["low"]},
            {k: high[k] for k in LEVEL_PARAMS["high"]},
        )

    async def test_streaming_path_yields_text_and_done(self):
        adapter = ScriptedAdapter()
        base_registry = SimpleNamespace(
            get_or_create=lambda *args, **kwargs: adapter, get_default=lambda: adapter,
        )
        engine = AgentEngine(
            model_registry=LevelAwareModelRegistry(base_registry, level_params("medium")),
            tool_registry=SimpleNamespace(),
            run_store=RunStorage(None),
        )
        engine._save_checkpoint = AsyncMock(return_value=None)
        engine._set_agent_mode = AsyncMock(return_value=None)
        engine._send_start_notification = AsyncMock(return_value=None)
        engine._send_completion_notification = AsyncMock(return_value=None)
        engine.sandbox = None
        engine.permission_overlay = None
        engine.agent_mode = None
        with patch("app.core.agent_engine.persist_message", new_callable=AsyncMock, return_value="m-1"):
            events = [event async for event in engine.run(make_session(), "hello")]
        kinds = [event.type for event in events]
        self.assertIn(AgentEventType.TEXT, kinds)
        self.assertIn(AgentEventType.DONE, kinds)


class RegistryProxyTests(unittest.TestCase):
    def test_proxy_injects_params_and_explicit_kwargs_win(self):
        base = ScriptedAdapter()
        registry = LevelAwareModelRegistry(SimpleNamespace(get_default=lambda: base), level_params("high"))
        adapter = registry.get_default()
        self.assertIs(adapter.capabilities, base.capabilities)
        self.assertEqual(base.calls, [])
        import asyncio

        async def one_turn():
            await adapter.chat([{"role": "user", "content": "hi"}])
            await adapter.chat([{"role": "user", "content": "hi"}], max_tokens=7)
            self.assertEqual(len(base.calls), 2)

        asyncio.run(one_turn())
        injected = base.calls[0]
        for key, value in LEVEL_PARAMS["high"].items():
            self.assertEqual(injected[key], value)
        self.assertEqual(base.calls[1]["max_tokens"], 7)
        self.assertEqual(base.calls[1]["temperature"], LEVEL_PARAMS["high"]["temperature"])


# ---------------------------------------------------------------------------
# HTTP endpoints: real router + SQLite + overridden auth
# ---------------------------------------------------------------------------


class ReasoningEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.database = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.addAsyncCleanup(self.database.dispose)
        async with self.database.begin() as connection:
            await connection.run_sync(lambda conn: Base.metadata.create_all(
                conn, tables=[SessionModel.__table__],
            ))
        self.db = async_sessionmaker(self.database, expire_on_commit=False)
        async with self.db() as db:
            db.add(SessionModel(
                id="s-1", user_id="owner-a", title="T", status="idle",
                context_data={"reasoning_level": "low"},
            ))
            db.add(SessionModel(id="s-2", user_id="owner-b", title="O", status="idle"))
            await db.commit()

        self.engine = SimpleNamespace(
            get_permission_config=lambda: None,
            update_permission_config=lambda config: None,
        )

        app = FastAPI()
        app.include_router(reasoning_module.router, prefix="/api/v1")
        app.dependency_overrides[reasoning_module.get_current_user] = lambda: "owner-a"
        app.dependency_overrides[reasoning_module.get_engine] = lambda: self.engine
        patcher = patch.object(reasoning_module, "async_session", self.db)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test",
        )
        self.addAsyncCleanup(self.client.aclose)

    async def test_levels_catalog(self):
        response = await self.client.get("/api/v1/reasoning/levels")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([entry["id"] for entry in body["levels"]], list(REASONING_LEVELS))
        self.assertEqual(body["default"], DEFAULT_REASONING_LEVEL)
        params = {entry["id"]: entry for entry in body["levels"]}
        self.assertNotEqual(params["low"], params["medium"])
        self.assertNotEqual(params["medium"], params["high"])

    async def test_get_session_level_reads_context_data(self):
        response = await self.client.get("/api/v1/reasoning/sessions/s-1/reasoning-level")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["level"], "low")
        self.assertEqual(body["params"], {**{"id": "low"}, **LEVEL_PARAMS["low"]})

    async def test_get_session_level_defaults_when_unset(self):
        async with self.db() as db:
            db.add(SessionModel(id="s-3", user_id="owner-a", title="N", status="idle"))
            await db.commit()
        response = await self.client.get("/api/v1/reasoning/sessions/s-3/reasoning-level")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["level"], DEFAULT_REASONING_LEVEL)

    async def test_get_other_users_session_is_404(self):
        response = await self.client.get("/api/v1/reasoning/sessions/s-2/reasoning-level")
        self.assertEqual(response.status_code, 404)

    async def test_put_updates_context_data(self):
        response = await self.client.put(
            "/api/v1/reasoning/sessions/s-1/reasoning-level", json={"level": "high"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["level"], "high")
        self.assertTrue(body["updated"])
        async with self.db() as db:
            row = await db.get(SessionModel, "s-1")
        self.assertEqual((row.context_data or {}).get("reasoning_level"), "high")

    async def test_put_preserves_other_context_keys(self):
        async with self.db() as db:
            row = await db.get(SessionModel, "s-1")
            row.context_data = {"reasoning_level": "low", "keep": "me"}
            await db.commit()
        response = await self.client.put(
            "/api/v1/reasoning/sessions/s-1/reasoning-level", json={"level": "medium"},
        )
        self.assertEqual(response.status_code, 200)
        async with self.db() as db:
            row = await db.get(SessionModel, "s-1")
        self.assertEqual(row.context_data, {"reasoning_level": "medium", "keep": "me"})

    async def test_put_unknown_level_is_422(self):
        response = await self.client.put(
            "/api/v1/reasoning/sessions/s-1/reasoning-level", json={"level": "warp"},
        )
        self.assertEqual(response.status_code, 422)
        async with self.db() as db:
            row = await db.get(SessionModel, "s-1")
        # The stored value must not change on a rejected update.
        self.assertEqual((row.context_data or {}).get("reasoning_level"), "low")

    async def test_put_on_other_users_session_is_404(self):
        response = await self.client.put(
            "/api/v1/reasoning/sessions/s-2/reasoning-level", json={"level": "high"},
        )
        self.assertEqual(response.status_code, 404)

    async def test_permission_tiers_report_mode_and_tool_states(self):
        from app.core.permission_rules import PermissionConfig, PermissionMode

        self.engine.get_permission_config = lambda: PermissionConfig(
            mode=PermissionMode.DEFAULT,
        )
        response = await self.client.get("/api/v1/reasoning/permission-tiers")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["current"], {"mode": "default", "tier": "full_write"})
        tier_ids = [tier["id"] for tier in body["tiers"]]
        self.assertEqual(tier_ids, ["read_only", "partial_write", "full_write"])
        states = {state["tool"]: state["decision"] for state in body["tool_states"]}
        # In default mode reads are automatic, mutations require confirmation.
        self.assertEqual(states["read_file"], "allow")
        self.assertEqual(states["write_file"], "ask")
        self.assertEqual(states["file_delete"], "ask")

    async def test_permission_tiers_handle_missing_engine_config(self):
        self.engine.get_permission_config = lambda: None
        response = await self.client.get("/api/v1/reasoning/permission-tiers")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsNone(body["current"]["mode"])
        self.assertIsNone(body["current"]["tier"])
        self.assertEqual(body["tool_states"], [])


if __name__ == "__main__":
    unittest.main()
