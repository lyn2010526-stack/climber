"""Pi 双层循环接线测试：Follow-up 自续跑入队去重 + 外层无进展守卫 + 自动续跑融合。"""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import AgentEventType, ChatResult
from app.core.agent_engine import (
    AgentEngine,
    _follow_up_hash,
    _outer_stall_update,
    _outer_turn_signature,
)
from app.core.checkpoint import InMemoryCheckpointStore
from app.core.engine.run_storage import RunStorage
from app.core.session import AgentSession, SessionConfig
from app.storage import Base
from app.storage.database import Agent, Message, Session, SessionInput, Turn, UsageLog
from app.storage.models_cost import CostRecord
from app.tools import ToolRegistry


class _FakeSession:
    def __init__(self, session_id="s") -> None:
        self.session_id = session_id
        self.user_id = "u"
        self.messages: list[dict] = []
        self.status = type("St", (), {"value": "completed"})()


class _FakeQueue:
    def __init__(self) -> None:
        self.submitted: list[dict] = []

    async def submit(self, session_id, user_id, client_request_id, kind, message):
        row = {
            "id": f"row-{len(self.submitted) + 1}",
            "client_request_id": client_request_id,
            "kind": kind, "message": message, "status": "queued",
        }
        if any(r["client_request_id"] == client_request_id for r in self.submitted):
            return next(r for r in self.submitted if r["client_request_id"] == client_request_id)
        self.submitted.append(row)
        return row


class FollowUpHashTests(unittest.TestCase):
    def test_hash_deterministic_and_stable(self) -> None:
        a = _follow_up_hash("检查日志并按模块汇总")
        b = _follow_up_hash("检查日志并按模块汇总")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 12)


class OuterStallGuardTests(unittest.TestCase):
    def test_signature_changes_on_progress(self) -> None:
        s1 = _FakeSession()
        s2 = _FakeSession()
        s2.messages.append({"role": "assistant", "content": "检查完成，汇总如下"})
        self.assertNotEqual(_outer_turn_signature(s1), _outer_turn_signature(s2))

    def test_signature_tracks_last_assistant_content(self) -> None:
        s1 = _FakeSession()
        s1.messages.append({"role": "assistant", "content": "第一版输出"})
        s2 = _FakeSession()
        s2.messages.append({"role": "assistant", "content": "第二版输出"})
        self.assertNotEqual(_outer_turn_signature(s1), _outer_turn_signature(s2))
        s3 = _FakeSession()
        s3.messages.append({"role": "assistant", "content": "第一版输出"})
        self.assertEqual(_outer_turn_signature(s1), _outer_turn_signature(s3))

    def test_signature_ignores_empty_outputs(self) -> None:
        s1 = _FakeSession()
        s1.messages.append({"role": "assistant", "content": ""})
        s2 = _FakeSession()
        s2.messages.append({"role": "assistant", "content": "   "})
        self.assertEqual(_outer_turn_signature(s1), _outer_turn_signature(s2))

    def test_stall_update_two_consecutive_same_signature(self) -> None:
        sig = ("completed", None)
        count, prev = _outer_stall_update(sig, None, 0)
        self.assertEqual((count, prev), (0, sig))
        count, prev = _outer_stall_update(sig, prev, count)
        self.assertEqual(count, 1)
        count, _ = _outer_stall_update(sig, prev, count)
        self.assertEqual(count, 2)

    def test_stall_update_resets_on_progress(self) -> None:
        sig = ("completed", None)
        count, prev = _outer_stall_update(sig, None, 0)
        count, prev = _outer_stall_update(sig, prev, count)
        self.assertEqual(count, 1)
        newer = ("completed", "新的输出内容")
        count, prev = _outer_stall_update(newer, prev, count)
        self.assertEqual(count, 0)


class EnqueueFollowUpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = AgentEngine.__new__(AgentEngine)  # noqa: SLF001
        self.engine._input_queue = _FakeQueue()  # noqa: SLF001

    def test_enqueue_dedupes_same_message(self) -> None:
        async def run() -> None:
            session = _FakeSession()
            first = await self.engine._enqueue_follow_up(session, "下一步：生成报告")
            second = await self.engine._enqueue_follow_up(session, "下一步：生成报告")
            third = await self.engine._enqueue_follow_up(session, "下一步：写入部署脚本")
            return first, second, third

        first, second, third = asyncio.run(run())
        self.assertEqual(first, second)
        self.assertNotEqual(first, third)
        queue = self.engine._input_queue
        self.assertEqual(len(queue.submitted), 2)
        self.assertTrue(all(i["kind"] == "follow_up" for i in queue.submitted))


class PiAutoContinueTests(unittest.IsolatedAsyncioTestCase):
    """End-to-end Pi dual-loop fusion: agent self-enqueues follow-ups, outer
    loop claims and auto-runs them, LOOP_STATUS is emitted, outer cap halts."""

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pi-auto-continue-")
        self.db_engine = create_async_engine("sqlite+aiosqlite:///" + str(Path(self.tmp.name) / "pi.db"))
        self.factory = async_sessionmaker(self.db_engine, expire_on_commit=False)
        tables = [m.__table__ for m in (Agent, Session, SessionInput, Turn, Message, UsageLog, CostRecord)]
        async with self.db_engine.begin() as conn:
            await conn.run_sync(lambda db: Base.metadata.create_all(db, tables=tables))
        async with self.factory() as db:
            db.add(Session(id="s", user_id="u", context_data={}))
            await db.commit()
        self.patches = []
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
            self.patches.append(p)

    async def asyncTearDown(self):
        for p in reversed(self.patches):
            p.stop()
        await self.db_engine.dispose()
        self.tmp.cleanup()

    def engine(self, responses, *, max_iterations=10):
        class ScriptedModel:
            capabilities = SimpleNamespace(streaming=False, max_tokens=100000)

            def __init__(self):
                self.responses = iter(responses)
                self.seen = []

            async def chat(self, messages, **_kwargs):
                self.seen.append([dict(m) for m in messages])
                return next(self.responses)

        model = ScriptedModel()
        registry = ToolRegistry()
        engine = AgentEngine(model_registry=SimpleNamespace(get_or_create=lambda **_kwargs: model),
                             tool_registry=registry, checkpoint_store=InMemoryCheckpointStore(),
                             run_store=RunStorage(self.factory))
        engine.sandbox = engine.permission_overlay = engine.agent_mode = None
        engine._validate_tool_call = Mock(return_value=(True, "scripted test tool"))
        engine._build_tools_for_session = Mock(return_value=[])
        for name in ("_set_agent_mode", "_send_start_notification", "_send_completion_notification",
                     "_send_failure_notification", "_trigger_memory_reflection", "_record_profile_outcome", "_tick_evolution"):
            setattr(engine, name, Mock())
        for name in ("_inject_memory_context", "_inject_core_memory", "_inject_profile_context",
                     "_store_episodic_memory", "_archive_instruction"):
            setattr(engine, name, AsyncMock())
        session = AgentSession(SessionConfig(session_id="s", user_id="u", agent_id="",
                                             provider="scripted", model_id="fake",
                                             max_iterations=max_iterations))
        session.context["pi_auto_continue"] = True
        return engine, session, model

    async def test_agent_self_enqueues_and_outer_loop_auto_runs(self):
        engine, session, _ = self.engine([ChatResult(content="第一轮结果"), ChatResult(content="第二轮结果")])
        engine._decide_followup = AsyncMock(
            side_effect=[
                {"finished": False, "next_subtask": "下一步：生成报告", "reason": "继续"},
                {"finished": True, "next_subtask": None, "reason": "任务完成"},
            ],
        )
        events = [e async for e in engine.run(session, "initial")]
        self.assertEqual(sum(e.type == AgentEventType.TURN_STARTED for e in events), 2)
        self.assertEqual(sum(e.type == AgentEventType.DONE for e in events), 1)
        final_done = next(e for e in events if e.type == AgentEventType.DONE)
        self.assertEqual(final_done.data["status"], "completed")
        loop_statuses = [e.data for e in events if e.type == AgentEventType.LOOP_STATUS]
        self.assertEqual(len(loop_statuses), 2)
        self.assertIn("下一步：生成报告", loop_statuses[0]["followup_queue"])
        self.assertEqual(loop_statuses[1]["outer_round"], 2)
        rows = await engine._input_queue.list("s", "u")  # noqa: SLF001
        self.assertEqual([r["message"] for r in rows], ["下一步：生成报告"])
        self.assertEqual(rows[0]["status"], "completed")
        self.assertEqual(rows[0]["kind"], "follow_up")

    async def test_finished_decision_enqueues_nothing(self):
        engine, session, _ = self.engine([ChatResult(content="直接完成")])
        engine._decide_followup = AsyncMock(
            return_value={"finished": True, "next_subtask": None, "reason": "done"},
        )
        events = [e async for e in engine.run(session, "initial")]
        self.assertEqual(sum(e.type == AgentEventType.TURN_STARTED for e in events), 1)
        self.assertEqual((await engine._input_queue.list("s", "u")), [])  # noqa: SLF001

    async def test_outer_cap_stops_auto_continue(self):
        engine, session, _ = self.engine([ChatResult(content="一轮即止")], max_iterations=1)
        engine._decide_followup = AsyncMock()
        events = [e async for e in engine.run(session, "initial")]
        engine._decide_followup.assert_not_called()  # noqa: SLF001
        final_done = next(e for e in events if e.type == AgentEventType.DONE)
        self.assertEqual(final_done.data["status"], "max_iterations_reached")

    async def test_opt_out_defaults_to_single_turn(self):
        engine, session, _ = self.engine([ChatResult(content="普通单轮")])
        session.context["pi_auto_continue"] = False
        events = [e async for e in engine.run(session, "initial")]
        self.assertEqual(sum(e.type == AgentEventType.TURN_STARTED for e in events), 1)
        self.assertEqual((await engine._input_queue.list("s", "u")), [])  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()