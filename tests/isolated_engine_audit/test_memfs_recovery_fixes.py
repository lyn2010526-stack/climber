"""Isolated unittest: regression coverage for wave3 db/memfs checkpoint fixes.

Covers R9-14 (recovery candidate discovery through the injected store),
R9-15 (PostgreSQL checkpoint upsert compiles), R12-H54 (CostRecord group
attribution), R12-H30 (core-memory block limit clamp), R12-N02 (MemFS init
gate), R12-H27 (git failures never break writes), R12-H28 (category inference
only for catalogued prefixes) and R12-H29 (lossless frontmatter round-trip).

No provider requests, credentials, shared database or pytest conftest are used.
Run: python3 -m unittest discover -s tests/isolated_engine_audit -v
"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import ChatResult
from app.core.checkpoint import CheckpointData, InMemoryCheckpointStore, SQLiteCheckpointStore
from app.core.core_memory import CoreMemoryService
from app.core.engine.run_storage import RunStorage
from app.core.memfs.memory_block import MemoryBlock
from app.core.memfs.store import MemFS
from app.core.recovery import RecoveryManager
from app.core.session import AgentSession
from app.storage import Base
from app.storage.database import (Agent, CheckpointRecord, Message, Session, SessionInput,
                                  Turn, UsageLog)
from app.storage.models_cost import CostRecord
from app.storage.models_memory import CoreMemoryBlock


def cost_reply():
    result = ChatResult(content="priced", tokens_used=3, tool_calls=[])
    result.usage = {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}
    result.input_cost = 0.01
    result.output_cost = 0.02
    result.total_cost = 0.03
    return result


class RecoveryAndCostFixes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="memfs-recovery-")
        self.addCleanup(self.tmp.cleanup)
        self.db_engine = create_async_engine("sqlite+aiosqlite:///" + str(Path(self.tmp.name) / "isolated.db"))
        self.addAsyncCleanup(self.db_engine.dispose)

        @event.listens_for(self.db_engine.sync_engine, "connect")
        def foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

        self.factory = async_sessionmaker(self.db_engine, expire_on_commit=False)
        tables = [model.__table__ for model in (Agent, Session, Turn, Message, UsageLog,
                                                CheckpointRecord, CostRecord, SessionInput,
                                                CoreMemoryBlock)]
        async with self.db_engine.begin() as connection:
            await connection.run_sync(lambda conn: Base.metadata.create_all(conn, tables=tables))

    async def rows(self, model):
        from sqlalchemy import select
        async with self.factory() as db:
            return list((await db.execute(select(model))).scalars().all())

    async def test_recovery_manager_discover_via_injected_memory_store(self):
        store = InMemoryCheckpointStore()
        await store.save(None, CheckpointData("session-a", [], 1, "processing"))
        await store.save(None, CheckpointData("session-b", [], 1, "completed"))
        manager = RecoveryManager(checkpoint_store=store)
        sessions = await manager.list_recoverable_sessions()
        self.assertEqual(sorted(row["session_id"] for row in sessions),
                         ["session-a", "session-b"])

    async def test_auto_recover_finds_in_memory_processing_checkpoint(self):
        store = InMemoryCheckpointStore()
        await store.save(None, CheckpointData("mem-session", [], 0, "processing"))
        manager = RecoveryManager(checkpoint_store=store)
        candidates = await manager.auto_recover()
        self.assertEqual([row["session_id"] for row in candidates], ["mem-session"])
        self.assertEqual(candidates[0]["status"], "recoverable")

    async def test_postgres_checkpoint_upsert_compiles(self):
        from sqlalchemy.dialects import postgresql

        captured = {}

        class _ExecutingSession:
            async def execute(self, stmt):
                captured["sql"] = str(stmt.compile(dialect=postgresql.dialect()))

            async def commit(self):
                pass

        class _SessionFactory:
            class _CM:
                async def __aenter__(self):
                    return _ExecutingSession()

                async def __aexit__(self, *args):
                    return False

            def __call__(self):
                return self._CM()

        fake_engine = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
        checkpoint = CheckpointData("pg-session", [{"role": "user", "content": "hi"}], 1, "processing")
        with patch("app.core.checkpoint.async_session", _SessionFactory()), \
                patch("app.storage.engine", fake_engine):
            store = SQLiteCheckpointStore()
            cid = await store.save(None, checkpoint)
        self.assertTrue(cid)
        self.assertIn("checkpoints", captured["sql"])
        self.assertIn("ON CONFLICT", captured["sql"])

    async def test_cost_record_carries_group_and_task_attribution(self):
        session = AgentSession(
            session_id="s-group", user_id="u1", agent_id=None,
            provider="p", model_id="m", api_key="k",
        )
        session.context["group_id"] = "grp-1"
        session.context["task_id"] = "task-42"
        store = RunStorage(self.factory)
        await store.begin(session)
        await store.record_response(session, cost_reply(), 1)
        rows = await self.rows(CostRecord)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].group_id, "grp-1")
        self.assertEqual(rows[0].task_id, "task-42")
        self.assertEqual(rows[0].total_cost, 0.03)

    async def test_cost_record_without_context_has_null_group(self):
        session = AgentSession(
            session_id="s-plain", user_id="u1", agent_id=None,
            provider="p", model_id="m", api_key="k",
        )
        store = RunStorage(self.factory)
        await store.begin(session)
        await store.record_response(session, cost_reply(), 1)
        rows = await self.rows(CostRecord)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0].group_id)
        self.assertIsNone(rows[0].task_id)

    async def test_core_memory_limit_is_clamped(self):
        service = CoreMemoryService()
        with patch("app.core.core_memory.async_session", self.factory):
            block = await service.create_or_update_block(
                "u1", "persona", "x" * 10000, limit=10 ** 9,
            )
            self.assertEqual(block.limit, 4096)
            self.assertEqual(len(block.value), 4096)
            low = await service.create_or_update_block(
                "u1", "bounded", "y" * 1000, limit=-5,
            )
            self.assertEqual(low.limit, 64)
            self.assertEqual(len(low.value), 64)

    async def test_messages_relationship_has_id_tiebreak(self):
        from app.storage.database import Session
        order_by = Session.messages.property.order_by
        rendered = ", ".join(str(expr) for expr in order_by)
        self.assertIn("messages.id", rendered)


class MemFsFixes(unittest.IsolatedAsyncioTestCase):
    def _tmp_base(self):
        return Path(tempfile.mkdtemp(prefix="memfs-store-"))

    def test_new_directory_is_git_initialized(self):
        base = self._tmp_base()
        store = MemFS(base_path=str(base), auto_commit=True)
        self.assertTrue(store.git_enabled)
        self.assertTrue((base / ".git").exists())

    def test_git_commit_failure_swallowed(self):
        base = self._tmp_base()
        store = MemFS(base_path=str(base), auto_commit=True)
        self.assertTrue(store.git_enabled)
        with patch("app.core.memfs.store.subprocess.run", side_effect=RuntimeError("git exploded")):
            store._git_commit_file("notes/a.md", "update")
            store._git_remove_file("notes/a.md")

    def test_write_block_survives_git_failure(self):
        base = self._tmp_base()
        store = MemFS(base_path=str(base), auto_commit=True)
        self.assertTrue(store.git_enabled)
        block = MemoryBlock(path="system/persona.md", content="hello")
        with patch("app.core.memfs.store.subprocess.run", side_effect=RuntimeError("git down")):
            store._write_block_sync(block)
        written = (base / "system" / "persona.md").read_text()
        self.assertIn("hello", written)

    def test_category_inference_only_for_catalogued_prefix(self):
        block = MemoryBlock(path="uncategorized/note.md", content="hi")
        self.assertNotIn("category", block.metadata)

    def test_category_inference_known_prefix(self):
        block = MemoryBlock(path="system/persona.md", content="hi")
        self.assertEqual(block.metadata["category"], "system")

    def test_frontmatter_round_trip_is_lossless(self):
        block = MemoryBlock(
            path="reference/example.md",
            content="# body",
            description="desc with : colon",
            metadata={
                "tags": ["a:b", "2024", "", "true", "x y"],
                "importance": 0.5,
                "nullable": None,
                "empty_string": "",
                "ticked": "code`x",
                "quoted": 'say "hi"',
                "newline": "line one\nline two",
            },
        )
        md = block.to_markdown()
        parsed = MemoryBlock.from_markdown(block.path, md)
        self.assertEqual(parsed.content, block.content)
        self.assertEqual(parsed.description, block.description)
        for key in ("tags", "importance", "nullable", "empty_string", "ticked", "quoted", "newline"):
            self.assertEqual(parsed.metadata.get(key), block.metadata[key],
                             f"key {key!r} changed on round-trip")


if __name__ == "__main__":
    unittest.main()
