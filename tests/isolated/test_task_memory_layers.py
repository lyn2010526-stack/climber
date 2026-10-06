"""Real ORM integration tests on private SQLite, run with unittest (no conftest)."""

# unittest assertions keep this suite independent of pytest and its shared DB fixtures.
# ruff: noqa: PT009, PT027

import asyncio
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.engine.task_memory import TaskMemory
from app.storage import Base
from app.storage.database import Agent, Session, SessionInput, Turn
from app.storage.models_instruction_traces import InstructionTrace


class TaskMemoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="task-memory-")
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{Path(self.tmp.name) / 'private.db'}")
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            tables = [model.__table__ for model in (Agent, Session, Turn, SessionInput, InstructionTrace)]
            await conn.run_sync(lambda db: Base.metadata.create_all(db, tables=tables))
        self.memory = TaskMemory(self.factory)
        async with self.factory() as db:
            db.add_all([Session(id="s", user_id="u"), Session(id="other", user_id="v"),
                        Session(id="same-owner", user_id="u")])
            await db.flush()
            db.add_all([
                Turn(id="t", session_id="s", status="completed", result="Implementation produced",
                     metadata_={"outcome": "completed", "cost_status": "unknown"}),
                Turn(id="failed", session_id="s", status="failed", error="Tool failed"),
                Turn(id="foreign", session_id="other", status="completed", result="PRIVATE"),
                Turn(id="sibling", session_id="same-owner", status="completed", result="SIBLING"),
                InstructionTrace(id="i", session_id="s", user_id="u", turn_id="t",
                                 raw_text="Implement goal", text_hash="hash", status="running",
                                 task_spec={"main_goal": "Implement goal", "constraints": ["Keep originals"]}),
                InstructionTrace(id="wrong-owner", session_id="s", user_id="v", turn_id="t",
                                 raw_text="PRIVATE", text_hash="wrong"),
                SessionInput(id="q", session_id="s", client_request_id="r1", kind="follow_up",
                             message="Next task", status="queued", sequence=1),
                SessionInput(id="a", session_id="s", client_request_id="r2", kind="steering",
                             message="Applied direction", status="applied", sequence=2),
                SessionInput(id="c", session_id="s", client_request_id="r3", kind="follow_up",
                             message="Run finished", status="completed", sequence=3),
            ])
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()
        self.tmp.cleanup()

    async def test_layers_real_states_and_sources(self):
        view = await self.memory.restore("s", "u", token_budget=10000)
        layers = view["layers"]
        self.assertEqual({x["source_id"] for x in layers["completed"]}, {"turn:t", "instruction:i", "input:c"})
        self.assertEqual({x["source_id"] for x in layers["todo"]}, {"turn:failed", "input:q", "input:a"})
        self.assertTrue(all(x["acceptance"] == "unverified" for rows in layers.values() for x in rows))
        self.assertNotIn("PRIVATE", view["task_context"])
        self.assertNotIn("SIBLING", view["task_context"])

    async def test_owner_session_and_turn_isolation(self):
        for operation in (self.memory.restore("s", "v"), self.memory.restore("missing", "u"),
                          self.memory.summarize_turn("s", "u", "foreign"),
                          self.memory.summarize_turn("s", "v", "t")):
            with self.assertRaises(LookupError):
                await operation

    async def test_budget_keeps_full_layers_and_valid_records(self):
        import json
        full = await self.memory.restore("s", "u", token_budget=10000)
        empty = await self.memory.restore("s", "u", token_budget=0)
        self.assertEqual(empty["layers"], full["layers"])
        self.assertEqual(empty["task_context"], "")
        for budget in (1, 200, 600):
            view = await self.memory.restore("s", "u", token_budget=budget)
            self.assertLessEqual(len(view["task_context"].encode()), budget)
            self.assertEqual(view["budget_used"], len(view["task_context"].encode()))
            lines = view["task_context"].splitlines()
            self.assertEqual(sum(map(len, view["layers"].values())), len(lines) + sum(view["omitted"].values()))
            for line in lines:
                self.assertIn(json.loads(line)["layer"], full["layers"])
        with self.assertRaises(ValueError):
            await self.memory.restore("s", "u", token_budget=-1)

    async def test_idempotent_summary_preserves_metadata_and_raw_records(self):
        summaries = await asyncio.gather(*(self.memory.summarize_turn("s", "u", "t") for _ in range(3)))
        self.assertEqual(summaries[0], summaries[1])
        self.assertEqual(summaries[1], summaries[2])
        self.assertEqual(summaries[0]["revision"], 1)
        self.assertFalse(any(x["source_id"].startswith("input:") for rows in summaries[0]["layers"].values() for x in rows))
        async with self.factory() as db:
            turn = await db.get(Turn, "t")
            self.assertEqual(turn.metadata_["cost_status"], "unknown")
            self.assertEqual(turn.result, "Implementation produced")
            self.assertEqual((await db.get(InstructionTrace, "i")).raw_text, "Implement goal")
            self.assertEqual(len((await db.scalars(select(SessionInput))).all()), 3)
            turn.status = "paused"
            turn.metadata_ = {**turn.metadata_, "outcome": "no_progress"}
            await db.commit()
        revised = await self.memory.summarize_turn("s", "u", "t")
        self.assertEqual(revised["revision"], 2)
        self.assertEqual(revised["layers"]["completed"], [])
        self.assertEqual(len(revised["layers"]["todo"]), 2)

    async def test_restore_independent_of_model_and_service_instance(self):
        before = await self.memory.restore("s", "u")
        await self.memory.summarize_turn("s", "u", "t")
        async with self.factory() as db:
            session = await db.get(Session, "s")
            session.model_settings = {"provider": "other", "model_id": "another-model"}
            await db.commit()
        restored = await TaskMemory(self.factory).restore("s", "u")
        self.assertEqual(before, restored)
        self.assertEqual(await self.memory.task_context("s", "u"), restored["task_context"])

    async def test_summary_trace_excluded_original_soft_archive_retained(self):
        async with self.factory() as db:
            db.add(InstructionTrace(id="summary", session_id="s", user_id="u",
                                    raw_text="Derived recap", text_hash="sum"))
            await db.flush()
            original = await db.get(InstructionTrace, "i")
            original.is_archived = True
            original.compressed_into_id = "summary"
            await db.commit()
        view = await self.memory.restore("s", "u")
        self.assertIn("instruction:i", {x["source_id"] for x in view["layers"]["planning"]})
        self.assertNotIn("instruction:summary", {x["source_id"] for x in view["layers"]["planning"]})

    async def test_failed_blocked_and_no_progress_stay_todo(self):
        async with self.factory() as db:
            turn = await db.get(Turn, "t")
            turn.metadata_ = {**turn.metadata_, "outcome": "no_progress"}
            queued = await db.get(SessionInput, "q")
            queued.status, queued.error = "blocked", "Review required"
            applied = await db.get(SessionInput, "a")
            applied.status, applied.error = "failed", "Execution failed"
            await db.commit()
        view = await self.memory.restore("s", "u", token_budget=10000)
        self.assertEqual({x["source_id"] for x in view["layers"]["completed"]}, {"input:c"})
        self.assertIn("turn:t", {x["source_id"] for x in view["layers"]["todo"]})
        self.assertIn("Review required", view["task_context"])

    async def test_unicode_raw_text_and_small_budget_are_preserved(self):
        text = "保留全部规划与待办\n" * 100
        async with self.factory() as db:
            original = await db.get(InstructionTrace, "i")
            original.raw_text = text
            await db.commit()
        summary = await self.memory.summarize_turn("s", "u", "t")
        self.assertEqual(summary["layers"]["planning"][0]["text"], text)
        view = await self.memory.restore("s", "u", token_budget=400)
        self.assertLessEqual(len(view["task_context"].encode("utf-8")), 400)
        self.assertEqual(view["layers"]["planning"][0]["text"], text)


if __name__ == "__main__":
    unittest.main()
