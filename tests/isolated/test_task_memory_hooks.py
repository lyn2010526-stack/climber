"""Private SQLite hook integration; scripted responses, real engine and storage."""

import asyncio
import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from anyio import CancelScope
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import AgentEvent, AgentEventType, ChatResult, ContextConfig
from app.core.agent_engine import AgentEngine
from app.core.checkpoint import InMemoryCheckpointStore
from app.core.engine.run_storage import RunStorage
from app.core.engine.runner import TASK_MEMORY_MARKER
from app.core.engine.task_memory import TaskMemory
from app.core.session import AgentSession, SessionConfig
from app.storage import Base
from app.storage.database import Agent, Message, Session, SessionInput, Turn, UsageLog
from app.storage.models_cost import CostRecord
from app.storage.models_instruction_traces import InstructionTrace


class TaskMemoryHookTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="task-memory-hooks-")
        self.db_engine = create_async_engine(
            f"sqlite+aiosqlite:///{Path(self.tmp.name) / 'private.db'}"
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
                    InstructionTrace,
                )
            ]
            await conn.run_sync(lambda db: Base.metadata.create_all(db, tables=tables))
        async with self.factory() as db:
            db.add(Session(id="s", user_id="u"))
            await db.flush()
            db.add(
                InstructionTrace(
                    id="old",
                    session_id="s",
                    user_id="u",
                    raw_text="Keep pending goal",
                    text_hash="old",
                    status="received",
                )
            )
            await db.commit()
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
            self.addCleanup(p.stop)
        self.session = AgentSession(
            SessionConfig(
                session_id="s",
                user_id="u",
                provider="scripted",
                model_id="fake",
                system_prompt="System policy",
                context_config=ContextConfig(max_tokens=16000),
            )
        )
        self.seen = []
        owner = self

        class ScriptedModel:
            capabilities = SimpleNamespace(streaming=True, max_tokens=16000)

            async def stream_chat(self, messages, **_kwargs):
                owner.seen.append(copy.deepcopy(messages))
                yield ChatResult(content="Scripted result", finish_reason="stop")

        self.engine = AgentEngine(
            model_registry=SimpleNamespace(get_or_create=lambda **_kw: ScriptedModel()),
            tool_registry=Mock(),
            checkpoint_store=InMemoryCheckpointStore(),
            run_store=RunStorage(self.factory),
        )
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
        ):
            setattr(self.engine, name, AsyncMock())

    async def asyncTearDown(self):
        await self.engine.resource_tracker.cleanup()
        await self.db_engine.dispose()
        self.tmp.cleanup()

    def contexts(self, messages):
        return [
            m
            for m in messages
            if m.get("role") == "system"
            and isinstance(m.get("content"), str)
            and m["content"].startswith(TASK_MEMORY_MARKER)
        ]

    async def test_real_run_restore_and_summary_committed_before_turn_done(self):
        for model in ("first-model", "second-model"):
            self.session.model_id = model
            async for event in self.engine.run(self.session, "Do this " + model):
                if event.type == AgentEventType.TURN_DONE:
                    async with self.factory() as db:
                        turn = await db.get(Turn, event.data["turn_id"])
                        self.assertEqual(turn.status, "completed")
                        self.assertEqual(turn.metadata_["task_memory"]["revision"], 1)
                        self.assertTrue(turn.metadata_["task_memory"]["layers"]["completed"])
            self.assertEqual(len(self.contexts(self.seen[-1])), 1)
            self.assertIn("instruction:old", self.contexts(self.seen[-1])[0]["content"])
        self.assertEqual(self.session.task_memory_summary_diagnostics["status"], "stored")
        async with self.factory() as db:
            self.assertEqual(len((await db.scalars(select(Turn))).all()), 2)

    async def test_compression_reinjects_through_facade_and_preserves_tool_pairs(self):
        pair = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"id": "tool1", "function": {"name": "read_file", "arguments": "{}"}}
                ],
            },
            {"role": "tool", "tool_call_id": "tool1", "content": "result"},
        ]
        self.session.messages.extend(
            [{"role": "system", "content": TASK_MEMORY_MARKER + " stale"}, *pair]
        )
        original = self.engine._inject_task_memory_context
        self.engine._inject_task_memory_context = AsyncMock(wraps=original)

        async def compress(session, adapter, compressor, *, meter=None):
            self.assertEqual(self.contexts(session.messages), [])
            return session.messages, 10

        with patch("app.core.engine.runner.compress_if_needed", side_effect=compress):
            events = [e async for e in self.engine.run(self.session, "New task")]
        self.engine._inject_task_memory_context.assert_awaited_once()
        messages = self.seen[-1]
        index = next(i for i, m in enumerate(messages) if m.get("tool_calls"))
        self.assertEqual(messages[index : index + 2], pair)
        self.assertEqual(len(self.contexts(messages)), 1)
        self.assertNotIn("stale", self.contexts(messages)[0]["content"])
        self.assertTrue(any(e.type == AgentEventType.CONTEXT_COMPRESSION for e in events))

    async def test_repeated_restore_clears_only_owned_system_context_and_bounds_budget(self):
        other = [
            {"role": "user", "content": TASK_MEMORY_MARKER + " quoted"},
            {"role": "system", "content": "Other memory"},
        ]
        self.session.messages.extend(other)
        for _ in range(2):
            await self.engine._inject_task_memory_context(self.session, token_budget=1000)
        self.assertEqual(len(self.contexts(self.session.messages)), 1)
        self.assertLessEqual(len(self.contexts(self.session.messages)[0]["content"].encode()), 1000)
        for msg in other:
            self.assertIn(msg, self.session.messages)
        await self.engine._inject_task_memory_context(self.session, token_budget=0)
        self.assertEqual(self.contexts(self.session.messages), [])

    async def test_failed_run_and_cancelled_run_summarized_after_cleanup(self):
        async def fail(session, message, *args):
            raise RuntimeError("scripted failure")
            yield AgentEvent(type=AgentEventType.DONE)

        self.engine._run_locked = fail
        with self.assertRaisesRegex(RuntimeError, "scripted failure"):
            _ = [e async for e in self.engine.run(self.session, "Fail")]
        async with self.factory() as db:
            turn = await db.get(Turn, self.session.current_turn_id)
            self.assertEqual(turn.status, "failed")
            self.assertEqual(turn.metadata_["task_memory"]["layers"]["completed"], [])

        async def cancel(session, message, *args):
            raise asyncio.CancelledError
            yield AgentEvent(type=AgentEventType.DONE)

        self.engine._run_locked = cancel
        with self.assertRaises(asyncio.CancelledError):
            _ = [e async for e in self.engine.run(self.session, "Cancel")]
        async with self.factory() as db:
            turn = await db.get(Turn, self.session.current_turn_id)
            self.assertEqual(turn.status, "stopped")
            self.assertEqual(turn.metadata_["task_memory"]["layers"]["completed"], [])

    async def test_nonstreaming_model_receives_restored_context(self):
        async def chat(messages, **_kwargs):
            self.seen.append(copy.deepcopy(messages))
            return ChatResult(content="Nonstreaming result", finish_reason="stop")

        adapter = SimpleNamespace(
            capabilities=SimpleNamespace(streaming=False, max_tokens=16000), chat=chat
        )
        self.engine.model_registry = SimpleNamespace(get_or_create=lambda **_kw: adapter)
        _ = [e async for e in self.engine.run(self.session, "Nonstreaming task")]
        self.assertEqual(len(self.contexts(self.seen[-1])), 1)
        self.assertIn("instruction:old", self.contexts(self.seen[-1])[0]["content"])
        async with self.factory() as db:
            turn = await db.get(Turn, self.session.current_turn_id)
            self.assertEqual(turn.metadata_["task_memory"]["revision"], 1)

    async def test_level_cancellation_shields_finish_and_summary(self):
        with CancelScope() as scope:
            async with self.engine._track_run_with_cleanup(self.session):
                scope.cancel()
                await asyncio.sleep(0)
        async with self.factory() as db:
            turn = await db.get(Turn, self.session.current_turn_id)
            self.assertEqual(turn.status, "stopped")
            self.assertEqual(turn.metadata_["task_memory"]["revision"], 1)
            self.assertEqual(turn.metadata_["task_memory"]["layers"]["completed"], [])

    async def test_hook_failures_logged_without_inventing_summary_or_changing_state(self):
        self.session.messages.append({"role": "system", "content": TASK_MEMORY_MARKER + " stale"})
        logger = Mock()
        with (
            patch("structlog.get_logger", return_value=logger),
            patch.object(
                TaskMemory,
                "restore",
                side_effect=LookupError("owner mismatch"),
            ),
        ):
            await self.engine._inject_task_memory_context(self.session)
        self.assertEqual(self.contexts(self.session.messages), [])
        self.assertEqual(self.session.task_memory_diagnostics["status"], "restore_failed")
        logger.warning.assert_called_once()
        with patch.object(
            TaskMemory, "summarize_turn", side_effect=RuntimeError("storage unavailable")
        ):
            _ = [e async for e in self.engine.run(self.session, "Run")]
        self.assertEqual(self.session.task_memory_summary_diagnostics["status"], "summary_failed")
        async with self.factory() as db:
            turn = await db.get(Turn, self.session.current_turn_id)
            self.assertEqual(turn.status, "completed")
            self.assertNotIn("task_memory", turn.metadata_)


if __name__ == "__main__":
    unittest.main()
