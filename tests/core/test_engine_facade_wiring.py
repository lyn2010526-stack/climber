"""Facade wiring regressions for the split AgentEngine.

The engine implementation lives in ``app.core.engine.*`` submodules; every
overridable behavior must stay reachable through the ``AgentEngine`` facade
so tests and subclasses keep a single interception point. This module pins
the high-risk wiring patterns identified in the split audit:

- the run() busy path must report an error without releasing or removing
  the active session lock (no concurrent runs on one session);
- ``ParallelToolExecutor`` validation must route through the facade
  ``_validate_tool_call`` override point;
- tool debug recovery must use ``engine.tool_registry`` (sessions never
  carry a ``_tool_registry`` attribute);
- ``run_locked`` must route through ``engine._iteration_loop`` so facade
  overrides of the main loop stay authoritative.
"""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import AgentEvent, AgentEventType, ChatResult
from app.core.agent_engine import AgentEngine
from app.core.engine.run_storage import RunStorage
from app.core.session import AgentSession, SessionConfig
from app.storage import Base
from app.storage.database import (
    Agent,
    CheckpointRecord,
    Document,
    Message,
    SessionInput,
    Turn,
    UsageLog,
)
from app.storage.database import Session as SessionRow
from app.storage.models_cost import CostRecord


class BlockedAdapter:
    """Non-streaming adapter whose chat call blocks until cancelled."""

    def __init__(self) -> None:
        self.capabilities = SimpleNamespace(streaming=False, max_tokens=100000)
        self.entered = asyncio.Event()

    async def chat(self, messages, tools=None, **kwargs):
        self.entered.set()
        await asyncio.Event().wait()

    async def stream_chat(self, messages, tools=None, **kwargs):
        yield ChatResult(content="done", finish_reason="stop")


class TextAdapter:
    """Streaming adapter yielding a single text chunk."""

    def __init__(self) -> None:
        self.capabilities = SimpleNamespace(streaming=True, max_tokens=100000)

    async def stream_chat(self, messages, tools=None, **kwargs):
        yield ChatResult(content="done", finish_reason="stop")


class FacadeWiringTests(unittest.IsolatedAsyncioTestCase):
    """Shared fixture: real engine loop over a private SQLite database."""

    async def asyncSetUp(self):
        self.engines = []
        tmp = tempfile.TemporaryDirectory(prefix="facade-wiring-")
        self.addAsyncCleanup(tmp.cleanup)
        self.db_engine = create_async_engine(
            "sqlite+aiosqlite:///" + str(Path(tmp.name) / "isolated.db"),
        )
        self.addAsyncCleanup(self.db_engine.dispose)
        self.factory = async_sessionmaker(self.db_engine, expire_on_commit=False)
        tables = [
            model.__table__
            for model in (
                Agent,
                SessionRow,
                Turn,
                Message,
                UsageLog,
                CheckpointRecord,
                CostRecord,
                Document,
                SessionInput,
            )
        ]
        async with self.db_engine.begin() as connection:
            await connection.run_sync(lambda conn: Base.metadata.create_all(conn, tables=tables))
        for target, replacement in (
            ("app.storage.async_session", self.factory),
            ("app.storage.engine", self.db_engine),
            ("app.core.ui_rules.async_session", self.factory),
            ("app.core.checkpoint.async_session", self.factory),
            ("app.core.prompt_optimizer.maybe_optimize_instruction", AsyncMock()),
            (
                "app.core.agent_engine.AgentEngine._init_sandbox",
                lambda engine: setattr(engine, "sandbox", None),
            ),
            ("app.core.agent_engine.AgentEngine._init_permissions", Mock()),
            ("app.core.agent_engine.AgentEngine._record_profile_outcome", Mock()),
            ("app.core.agent_engine.AgentEngine._tick_evolution", Mock()),
        ):
            p = patch(target, replacement)
            p.start()
            self.addCleanup(p.stop)
        self.addAsyncCleanup(self.cleanup_engines)

    async def cleanup_engines(self):
        for engine in self.engines:
            await engine.resource_tracker.cleanup()
            while engine._background_tasks:
                await asyncio.gather(*list(engine._background_tasks), return_exceptions=True)

    def make_session(self, sid="wire-1"):
        return AgentSession(
            SessionConfig(
                session_id=sid,
                agent_id="",
                user_id="u-1",
                provider="scripted",
                model_id="fake-model",
            )
        )

    def make_engine(self, adapter) -> AgentEngine:
        registry = SimpleNamespace(get_or_create=lambda *a, **k: adapter)
        engine = AgentEngine(
            model_registry=registry,
            tool_registry=Mock(),
            run_store=RunStorage(self.factory),
        )
        self.engines.append(engine)
        engine.sandbox = None
        engine.permission_overlay = None
        engine.agent_mode = None
        engine._build_tools_for_session = Mock(return_value=[])
        for name in (
            "_set_agent_mode",
            "_send_start_notification",
            "_send_completion_notification",
            "_send_failure_notification",
            "_trigger_memory_reflection",
        ):
            setattr(engine, name, Mock(return_value=None))
        for name in (
            "_inject_memory_context",
            "_inject_core_memory",
            "_store_episodic_memory",
            "_inject_profile_context",
            "_archive_instruction",
        ):
            setattr(engine, name, AsyncMock(return_value=None))
        return engine

    async def test_busy_run_reports_error_and_keeps_active_lock(self):
        engine = self.make_engine(BlockedAdapter())
        session = self.make_session()
        first = engine.run(session, "first")
        await anext(first)
        second = [item async for item in engine.run(session, "second")]
        self.assertEqual(second[0].type, AgentEventType.ERROR)
        self.assertIn("busy", second[0].data["error"])
        # The busy path must not pop or release the lock held by the first run.
        self.assertIn(session.session_id, engine._session_locks)
        self.assertTrue(engine._session_locks[session.session_id].locked())
        await first.aclose()
        # Only the completing run removes its own lock.
        self.assertNotIn(session.session_id, engine._session_locks)

    async def test_lock_is_recreated_after_run_finishes(self):
        engine = self.make_engine(TextAdapter())
        session = self.make_session()
        events = [item async for item in engine.run(session, "one")]
        self.assertTrue(any(item.type == AgentEventType.DONE for item in events))
        self.assertNotIn(session.session_id, engine._session_locks)
        again = [item async for item in engine.run(session, "two")]
        self.assertTrue(any(item.type == AgentEventType.DONE for item in again))

    async def test_saved_ui_rules_reach_next_model_iteration(self):
        from app.core.ui_rules import save_rule

        captured = []

        class CapturingAdapter(TextAdapter):
            async def stream_chat(self, messages, tools=None, **kwargs):
                captured.append([dict(message) for message in messages])
                async for chunk in super().stream_chat(messages, tools, **kwargs):
                    yield chunk

        first = await save_rule("u-1", "project", "first rule", None)
        engine = self.make_engine(CapturingAdapter())
        session = self.make_session()
        events = [item async for item in engine.run(session, "one")]
        self.assertTrue(any(item.type == AgentEventType.DONE for item in events))
        self.assertTrue(any("first rule" in str(m["content"]) for m in captured[-1]))
        await save_rule("u-1", "project", "second rule", first["revision"])
        events = [item async for item in engine.run(session, "two")]
        self.assertTrue(any(item.type == AgentEventType.DONE for item in events))
        self.assertTrue(any("second rule" in str(m["content"]) for m in captured[-1]))
        self.assertFalse(any("first rule" in str(m["content"]) for m in captured[-1]))

    async def test_run_locked_routes_through_facade_iteration_loop(self):
        engine = self.make_engine(TextAdapter())
        session = self.make_session()
        seen: list[AgentSession] = []

        async def fake_iteration_loop(session, executor, compressor):
            seen.append(session)
            yield AgentEvent(type=AgentEventType.DONE, data={"status": "completed"})

        engine._iteration_loop = fake_iteration_loop
        events = [item async for item in engine._run_locked(session, "hello")]
        self.assertEqual(seen, [session])
        # The override's event comes through first, then run_locked's own DONE.
        self.assertEqual(
            events[0], AgentEvent(type=AgentEventType.DONE, data={"status": "completed"})
        )
        self.assertEqual(events[-1].type, AgentEventType.DONE)

    async def test_run_routes_through_facade_run_locked(self):
        engine = self.make_engine(TextAdapter())
        session = self.make_session()

        async def fake_run_locked(session, message, images=None, attachments=None):
            yield AgentEvent(type=AgentEventType.TEXT, data={"content": "hi"})

        engine._run_locked = fake_run_locked
        events = [item async for item in engine.run(session, "hello")]
        self.assertEqual(
            [item.type for item in events],
            [
                AgentEventType.TURN_STARTED,
                AgentEventType.RUNTIME_REPORT,
                AgentEventType.TEXT,
                AgentEventType.TURN_DONE,
                AgentEventType.LOOP_STATUS,
                AgentEventType.RUNTIME_REPORT,
                AgentEventType.DONE,
            ],
        )

    async def test_parallel_executor_validator_routes_through_facade(self):
        engine = self.make_engine(TextAdapter())
        session = self.make_session()
        engine._validate_tool_call = Mock(return_value=(False, "blocked-by-facade"))
        executor = engine._make_parallel_executor(session)
        tool_call = {
            "id": "c1",
            "type": "function",
            "function": {"name": "any_tool", "arguments": {"x": 1}},
        }
        results = await executor.execute_all([tool_call])
        engine._validate_tool_call.assert_called_once_with(session, "any_tool", {"x": 1})
        self.assertFalse(results[0].success)
        self.assertIn("blocked-by-facade", results[0].error)

    async def test_subclass_override_of_validator_is_used(self):
        class OverridingEngine(AgentEngine):
            def __init__(self, adapter, factory):
                super().__init__(
                    model_registry=SimpleNamespace(get_or_create=lambda *a, **k: adapter),
                    tool_registry=Mock(),
                    run_store=RunStorage(factory),
                )
                self.override_calls: list[tuple] = []

            def _validate_tool_call(self, session, tool_name, arguments):
                self.override_calls.append((tool_name, arguments))
                return False, "subclass-says-no"

        engine = OverridingEngine(TextAdapter(), self.factory)
        self.engines.append(engine)
        session = self.make_session()
        executor = engine._make_parallel_executor(session)
        tool_call = {
            "id": "c1",
            "type": "function",
            "function": {"name": "any_tool", "arguments": {}},
        }
        results = await executor.execute_all([tool_call])
        self.assertEqual(engine.override_calls, [("any_tool", {})])
        self.assertFalse(results[0].success)
        self.assertIn("subclass-says-no", results[0].error)

    async def test_tool_debug_recovery_uses_engine_registry(self):
        engine = self.make_engine(TextAdapter())
        session = self.make_session()
        # The audited defect: sessions must never be expected to carry a registry.
        self.assertFalse(hasattr(session, "_tool_registry"))

        recovered = SimpleNamespace(success=True, output="fixed-output")
        callbacks: list = []

        class FakeDebugLoop:
            async def recover(self, tool_name, arguments, error_output, retry_callback):
                callbacks.append(retry_callback)
                return recovered

        engine.debug_loop = FakeDebugLoop()
        execute = Mock(return_value="raw-retry-output")
        engine.tool_registry = SimpleNamespace(execute=execute)

        tr = SimpleNamespace(
            tool_name="broken_tool",
            arguments={"a": 1},
            error="boom",
            result="",
            success=False,
            duration_ms=1,
        )
        await engine._handle_tool_debug(session, tr)
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(tr.error, "")
        self.assertEqual(tr.result, "fixed-output")
        # The retry callback goes through the engine's registry.
        self.assertEqual(callbacks[0]("broken_tool", {"a": 1}), "raw-retry-output")
        execute.assert_called_once_with("broken_tool", {"a": 1})


if __name__ == "__main__":
    unittest.main()
