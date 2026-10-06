"""Backend reliability: agent checkpoints survive a store restart."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.checkpoint import CheckpointData, SQLiteCheckpointStore
from app.core.recovery import RecoveryManager
from app.core.session import AgentSession, SessionConfig
from app.storage import Base
from app.storage.database import CheckpointRecord, Session, Turn


class CheckpointPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="checkpoint-dur-")
        self.addCleanup(self.tmp.cleanup)
        self.db_engine = create_async_engine(
            "sqlite+aiosqlite:///" + str(Path(self.tmp.name) / "cp.db")
        )
        self.addAsyncCleanup(self.db_engine.dispose)
        self.factory = async_sessionmaker(self.db_engine, expire_on_commit=False)
        async with self.db_engine.begin() as conn:
            await conn.run_sync(
                lambda db: Base.metadata.create_all(
                    db, tables=[CheckpointRecord.__table__, Session.__table__, Turn.__table__]
                )
            )
        self.patches = [
            patch("app.core.checkpoint.async_session", self.factory),
            patch("app.storage.async_session", self.factory),
            patch("app.storage.engine", self.db_engine),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    async def test_checkpoint_survives_store_restart(self):
        first = SQLiteCheckpointStore()
        checkpoint = CheckpointData(
            session_id="s-cp",
            messages=[{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}],
            iteration=4,
            status="completed",
            channel_values={"final_content": "hello"},
        )
        cid = await first.save(None, checkpoint, thread_id="turn-1")
        self.assertTrue(cid)

        reopened = SQLiteCheckpointStore()
        latest = await reopened.get_latest(None, "s-cp")
        self.assertIsNotNone(latest)
        restored, _restored_id = latest
        self.assertEqual(restored.iteration, 4)
        self.assertEqual(restored.messages[0]["content"], "hi")
        self.assertEqual(restored.messages[1]["content"], "hello")
        self.assertEqual(restored.status, "completed")
        self.assertEqual(restored.channel_values, {"final_content": "hello"})

        AgentSession(
            SessionConfig(
                session_id="s-cp", user_id="u", agent_id="", provider="scripted", model_id="fake"
            )
        )
        manager = RecoveryManager(reopened)
        recovered = await manager.recover_session("s-cp")
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered["iteration"], 4)
        self.assertEqual(len(recovered["messages"]), 2)
        candidates = await manager.list_recoverable_sessions()
        self.assertTrue(any(item["session_id"] == "s-cp" for item in candidates))

    async def test_checkpoint_restores_session_state(self):
        store = SQLiteCheckpointStore()
        checkpoint = CheckpointData(
            session_id="s-cp2",
            messages=[
                {"role": "user", "content": "build a report"},
                {"role": "assistant", "content": "done"},
            ],
            iteration=2,
            status="completed",
            channel_values={"final_result": "done"},
        )
        await store.save(None, checkpoint, thread_id="turn-1")
        session = AgentSession(
            SessionConfig(
                session_id="s-cp2", user_id="u", agent_id="", provider="scripted", model_id="fake"
            )
        )
        self.assertTrue(await RecoveryManager(store).restore_session(session))
        self.assertEqual(len(session.messages), 2)
        self.assertEqual(session._last_iteration, 2)

    async def test_interrupted_checkpoint_flags_resume(self):
        store = SQLiteCheckpointStore()
        checkpoint = CheckpointData(
            session_id="s-cp3",
            messages=[{"role": "user", "content": "investigate"}],
            iteration=5,
            status="running",
            channel_values={"step": "mid-flight"},
        )
        await store.save(None, checkpoint, thread_id="turn-1")
        session = AgentSession(
            SessionConfig(
                session_id="s-cp3", user_id="u", agent_id="", provider="scripted", model_id="fake"
            )
        )
        recovered = await RecoveryManager(store).recover_session("s-cp3")
        self.assertIsNotNone(recovered)
        self.assertTrue(recovered["interrupted"])
        self.assertTrue(await RecoveryManager(store).restore_session(session))
        self.assertEqual(session._last_iteration, 5)
        self.assertTrue(session._resume_interrupted)
