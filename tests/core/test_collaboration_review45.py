"""Run with unittest discovery; never load tests/conftest.py.

Real: ORM, handoff message, entry/dispatch, planner/prompts, simple/retry runner.
Replaced: session factories (temporary SQLite), run_agent (scripted events),
credential resolution, websocket transport and result-memory side effects.
Retry cases also control retry count and fallback selection, not the runners.
The handoff constructor spy delegates to the real dataclass. No live LLM.
"""

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Isolate storage initialization as well as every session used by this suite.
with patch.dict(os.environ, {
    "APP_TESTING": "true",
    "TEST_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
}):
    from app.core import AgentEvent, AgentEventType
    from app.core.collaboration import agent_runner, base, checkpoint, handoff, hierarchical
    from app.storage import Base
    from app.storage.models_groups import (
        AgentGroup, AgentGroupMember, AgentGroupTask, AgentGroupTaskCheckpoint,
    )


class CollaborationReview45Tests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        directory = tempfile.TemporaryDirectory(prefix="collaboration-review45-")
        self.addCleanup(directory.cleanup)
        url = f"sqlite+aiosqlite:///{Path(directory.name) / 'tasks.db'}"
        self.db_engine = create_async_engine(url)
        self.addAsyncCleanup(self.db_engine.dispose)

        @event.listens_for(self.db_engine.sync_engine, "connect")
        def enable_foreign_keys(connection, _):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.sessions = async_sessionmaker(self.db_engine, expire_on_commit=False)
        async with self.db_engine.begin() as connection:
            await connection.run_sync(
                Base.metadata.create_all,
                tables=[model.__table__ for model in (
                    AgentGroup, AgentGroupMember, AgentGroupTask, AgentGroupTaskCheckpoint,
                )],
            )
        for module in (base, hierarchical, checkpoint):
            self.enterContext(patch.object(module, "async_session", self.sessions))
        self.broadcast = self.enterContext(
            patch.object(base.group_ws_hub, "broadcast", new_callable=AsyncMock)
        )
        self.memory = self.enterContext(
            patch.object(hierarchical, "store_memory", new_callable=AsyncMock)
        )
        self.enterContext(patch.object(hierarchical, "resolve_api_key", return_value="test-only"))
        self.enterContext(patch.object(hierarchical, "resolve_base_url", return_value=None))
        self.calls = []
        self.responses = ["Assign work to worker-agent", "worker result", "approved"]

        async def scripted_agent(*args, **kwargs):
            self.calls.append({"agent_id": args[0], "model_id": args[2], "prompt": args[5]})
            response = self.responses.pop(0)
            if isinstance(response, BaseException):
                raise response
            if isinstance(response, AgentEvent):
                yield response
                return
            if isinstance(response, list):
                for event in response:
                    yield event
                return
            yield AgentEvent(AgentEventType.TEXT, {"content": response})
            yield AgentEvent(AgentEventType.DONE, {"status": "completed", "tokens_used": 7})

        self.enterContext(patch.object(agent_runner, "run_agent", scripted_agent))
        self.engine = base.GroupCollaborationEngine(None, None)
        async with self.sessions() as db:
            self.manager = AgentGroupMember(id="manager-member", agent_id="manager-agent", role="manager")
            self.worker = AgentGroupMember(id="worker-member", agent_id="worker-agent", role="worker")
            self.target = AgentGroupMember(id="target-member", agent_id="target-agent", role="reviewer")
            self.group = AgentGroup(
                id="group", name="Review 4/5", process_type="hierarchical",
                manager_agent_id=self.manager.id, members=[self.manager, self.worker, self.target],
            )
            foreign_group = AgentGroup(
                id="foreign-group", name="Other group",
                members=[AgentGroupMember(id="foreign-member", agent_id="foreign-agent")],
            )
            db.add_all([self.group, foreign_group])
            await db.flush()
            self.task = AgentGroupTask(
                id="task", group_id=self.group.id, description="Review the implementation",
                worker_id=self.worker.id, status="pending",
            )
            db.add(self.task)
            await db.commit()

    async def persisted_task(self):
        async with self.sessions() as db:
            return await db.get(AgentGroupTask, self.task.id)

    def events(self, kind):
        return [call.args[1]["data"] for call in self.broadcast.await_args_list
                if call.args[1]["type"] == kind]

    async def assert_failed(self, message):
        task = await self.persisted_task()
        self.assertEqual(task.status, "failed")
        self.assertIsNone(task.final_output)
        self.assertEqual(len(self.events("task_failed")), 1)
        self.assertIn(message, self.events("task_failed")[0]["error"])
        self.assertEqual(self.events("task_completed"), [])
        self.assertEqual(self.engine._running_tasks, {})
        self.memory.assert_not_awaited()

    async def test_handoff_constructs_real_message_and_persists_member_ids(self):
        message_type = handoff.HandoffMessage
        messages = []

        def capture(**kwargs):
            message = message_type(**kwargs)
            messages.append(message)
            return message

        with patch.object(handoff, "HandoffMessage", side_effect=capture):
            result = await self.engine.handoff_task("task", "target-agent", "Review needed")
        self.assertEqual(result, {"ok": True, "task_id": "task", "handoff_to": "target-member"})
        self.assertEqual(len(messages), 1)
        self.assertIsInstance(messages[0], message_type)
        self.assertEqual(vars(messages[0]), {
            "source_agent": "worker-member", "target_agent": "target-member",
            "task_id": "task", "context": self.task.description, "reason": "Review needed",
        })
        self.assertIsInstance(messages[0].context, str)
        task = await self.persisted_task()
        self.assertEqual(task.worker_id, "target-member")
        self.assertEqual(task.status, "pending")
        self.assertEqual(self.events("task_handoff"), [{
            "task_id": "task", "from_agent": "worker-member",
            "to_agent": "target-member", "reason": "Review needed",
        }])

    async def test_handoff_missing_task_returns_404_without_event(self):
        with self.assertRaises(HTTPException) as raised:
            await self.engine.handoff_task("missing", "target-agent")
        self.assertEqual(raised.exception.status_code, 404)
        self.broadcast.assert_not_awaited()

    async def test_handoff_invalid_targets_leave_assignment_unchanged(self):
        for target in ("missing", "foreign-agent", "target-member"):
            with self.subTest(target=target), self.assertRaises(HTTPException) as raised:
                await self.engine.handoff_task("task", target)
            self.assertEqual(raised.exception.status_code, 404)
            task = await self.persisted_task()
            self.assertEqual(task.worker_id, "worker-member")
            self.assertEqual(task.status, "pending")
        self.broadcast.assert_not_awaited()

    async def test_handoff_without_source_uses_empty_member_id(self):
        async with self.sessions() as db:
            task = await db.get(AgentGroupTask, "task")
            task.worker_id = None
            await db.commit()
        await self.engine.handoff_task("task", "target-agent")
        self.assertEqual(self.events("task_handoff")[0]["from_agent"], "")
        self.assertEqual((await self.persisted_task()).worker_id, "target-member")

    async def test_planner_executes_with_real_task_and_group_members(self):
        self.assertFalse(hasattr(self.task, "group_members"))
        plan = await hierarchical._plan_subtasks(self.task, self.manager, self.group.members)
        self.assertEqual(plan, "Assign work to worker-agent")
        prompt = self.calls[0]["prompt"]
        self.assertIn(self.task.description, prompt)
        self.assertIn("- worker-agent (worker)", prompt)
        self.assertIn("- target-agent (reviewer)", prompt)
        self.assertNotIn("- manager-agent (manager)", prompt)

    async def test_entry_reaches_real_planner_and_completes(self):
        await self.engine.run_task("task")
        task = await self.persisted_task()
        self.assertEqual(task.status, "completed")
        self.assertEqual(task.final_output, "approved")
        self.assertIsNotNone(task.completed_at)
        self.assertEqual([call["agent_id"] for call in self.calls],
                         ["manager-agent", "worker-agent", "manager-agent"])
        self.assertIn("- worker-agent (worker)", self.calls[0]["prompt"])
        self.assertEqual(len(self.events("task_completed")), 1)
        self.assertEqual(self.events("task_failed"), [])
        self.assertEqual(self.engine._running_tasks, {})
        self.memory.assert_awaited_once()

    async def test_planner_propagates_error_with_cause(self):
        error = RuntimeError("planner unavailable")
        self.responses = [error]
        with self.assertRaisesRegex(RuntimeError, "Manager planning failed") as raised:
            await hierarchical._plan_subtasks(self.task, self.manager, self.group.members)
        self.assertIs(raised.exception.__cause__, error)

    async def test_entry_persists_planner_error_event_as_failed(self):
        self.responses = [AgentEvent(AgentEventType.ERROR, {"error": "planner unavailable"})]
        await self.engine.run_task("task")
        await self.assert_failed("planner unavailable")
        self.assertEqual(len(self.calls), 1)

    async def test_entry_persists_planner_timeout_as_failed(self):
        self.responses = [TimeoutError("deadline exceeded")]
        await self.engine.run_task("task")
        await self.assert_failed("deadline exceeded")

    async def test_entry_rejects_empty_plan(self):
        self.responses = ["  "]
        await self.engine.run_task("task")
        await self.assert_failed("empty plan")
        self.assertEqual(len(self.calls), 1)

    async def test_entry_persists_validation_error_as_failed(self):
        self.responses[-1] = RuntimeError("validation unavailable")
        await self.engine.run_task("task")
        await self.assert_failed("Manager validation failed")
        self.assertEqual(len(self.calls), 3)

    async def test_entry_missing_manager_fails(self):
        async with self.sessions() as db:
            group = await db.get(AgentGroup, "group")
            group.manager_agent_id = None
            for member_id in ("manager-member", "worker-member"):
                member = await db.get(AgentGroupMember, member_id)
                member.role = "observer"
            await db.commit()
        await self.engine.run_task("task")
        await self.assert_failed("No manager found")
        self.assertEqual(self.calls, [])

    async def test_entry_missing_workers_fails(self):
        async with self.sessions() as db:
            worker = await db.get(AgentGroupMember, "worker-member")
            worker.role = "observer"
            await db.commit()
        await self.engine.run_task("task")
        await self.assert_failed("No workers found")
        self.assertEqual(self.calls, [])

    async def test_cancellation_keeps_stopped_status_and_propagates(self):
        self.responses = [asyncio.CancelledError()]
        with self.assertRaises(asyncio.CancelledError):
            await self.engine.run_task("task")
        self.assertEqual((await self.persisted_task()).status, "stopped")
        self.assertEqual(self.events("task_failed"), [])
        self.assertEqual(self.engine._running_tasks, {})

    async def run_worker_with_retry(self):
        return await agent_runner.run_agent_with_retry(
            agent_id="worker-agent", provider="openai", model_id="gpt-4o",
            api_key="test-only", system_prompt="worker", user_message="task",
            tools=[], group_id="group", role="worker",
        )

    async def test_exhausted_worker_and_fallback_persist_failed_before_validation(self):
        self.responses = ["plan", RuntimeError("primary failed"),
                          RuntimeError("fallback failed"), "approved"]
        with patch.object(agent_runner, "MAX_RETRIES", 0), patch.object(
            agent_runner, "_get_fallback_model", return_value=("openai", "test-fallback")
        ):
            await self.engine.run_task("task")
        await self.assert_failed("worker failed after retry")
        self.assertEqual([call["agent_id"] for call in self.calls],
                         ["manager-agent", "worker-agent", "worker-agent"])
        self.assertEqual(self.responses, ["approved"])

    async def test_retry_exhaustion_preserves_last_exception_cause(self):
        for fallback in (None, ("openai", "test-fallback")):
            with self.subTest(fallback=fallback):
                errors = [RuntimeError("primary failed"), TimeoutError("retry timed out")]
                if fallback:
                    errors.append(ValueError("fallback failed"))
                last_error = errors[-1]
                self.responses = list(errors)
                self.calls.clear()
                with patch.object(agent_runner, "MAX_RETRIES", 1), patch.object(
                    agent_runner, "_get_fallback_model", return_value=fallback
                ), self.assertRaisesRegex(RuntimeError, "worker failed after retry") as raised:
                    await self.run_worker_with_retry()
                self.assertIs(raised.exception.__cause__, last_error)
                self.assertEqual(len(self.calls), len(errors))
                self.assertEqual(self.responses, [])

    async def test_worker_cancellation_in_primary_or_fallback_stays_stopped(self):
        for in_fallback in (False, True):
            with self.subTest(in_fallback=in_fallback):
                self.responses = ["plan"]
                if in_fallback:
                    self.responses.append(RuntimeError("primary failed"))
                cancelled = asyncio.CancelledError()
                self.responses.extend([cancelled, "approved"])
                self.calls.clear()
                self.broadcast.reset_mock()
                with patch.object(agent_runner, "MAX_RETRIES", 0), patch.object(
                    agent_runner, "_get_fallback_model", return_value=("openai", "test-fallback")
                ) as fallback, self.assertRaises(asyncio.CancelledError) as raised:
                    await self.engine.run_task("task")
                self.assertIs(raised.exception, cancelled)
                self.assertEqual((await self.persisted_task()).status, "stopped")
                self.assertEqual(len(self.calls), 3 if in_fallback else 2)
                self.assertEqual(fallback.call_count, int(in_fallback))
                self.assertEqual(self.responses, ["approved"])
                self.assertEqual(self.events("task_failed"), [])
                self.assertEqual(self.events("task_completed"), [])
                self.assertEqual(self.engine._running_tasks, {})
                self.memory.assert_not_awaited()

    async def test_tool_only_done_succeeds_in_primary_retry_and_fallback(self):
        for mode in ("primary", "retry", "fallback"):
            with self.subTest(mode=mode):
                tool_completion = [
                    AgentEvent(AgentEventType.TOOL_CALL, {"name": "test_tool"}),
                    AgentEvent(AgentEventType.TOOL_RESULT, {"result": "ok"}),
                    AgentEvent(AgentEventType.DONE, {"status": "completed", "tokens_used": 11}),
                ]
                self.responses = [] if mode == "primary" else [RuntimeError("transient failure")]
                self.responses.append(tool_completion)
                self.calls.clear()
                with patch.object(agent_runner, "MAX_RETRIES", int(mode == "retry")), patch.object(
                    agent_runner, "_get_fallback_model", return_value=("openai", "test-fallback")
                ) as fallback:
                    result = await self.run_worker_with_retry()
                self.assertEqual(result, ("", 11))
                self.assertEqual(len(self.calls), 1 if mode == "primary" else 2)
                self.assertEqual(fallback.call_count, int(mode == "fallback"))
                self.assertEqual(self.calls[-1]["model_id"],
                                 "test-fallback" if mode == "fallback" else "gpt-4o")
                self.assertEqual(self.responses, [])

    async def test_entry_accepts_tool_only_fallback_completion(self):
        self.responses = ["plan", RuntimeError("primary failed"), [
            AgentEvent(AgentEventType.TOOL_CALL, {"name": "test_tool"}),
            AgentEvent(AgentEventType.TOOL_RESULT, {"result": "ok"}),
            AgentEvent(AgentEventType.DONE, {"status": "completed", "tokens_used": 11}),
        ], "approved"]
        with patch.object(agent_runner, "MAX_RETRIES", 0), patch.object(
            agent_runner, "_get_fallback_model", return_value=("openai", "test-fallback")
        ):
            await self.engine.run_task("task")
        self.assertEqual((await self.persisted_task()).status, "completed")
        self.assertEqual(self.events("task_failed"), [])
        self.assertEqual(len(self.events("task_completed")), 1)
        self.assertEqual(self.events("hierarchical_delegate_done")[0]["tokens_used"], 11)
        self.assertEqual(self.responses, [])

    async def test_stream_without_done_raises_instead_of_succeeding(self):
        for events in ([], [AgentEvent(AgentEventType.TEXT, {"content": "partial output"})]):
            with self.subTest(events=events):
                self.responses = [events]
                with patch.object(agent_runner, "MAX_RETRIES", 0), patch.object(
                    agent_runner, "_get_fallback_model", return_value=None
                ), self.assertRaisesRegex(RuntimeError, "worker failed after retry") as raised:
                    await self.run_worker_with_retry()
                self.assertIsInstance(raised.exception.__cause__, RuntimeError)
                self.assertIn("DONE", str(raised.exception.__cause__))

    async def test_error_event_after_partial_text_is_failed(self):
        self.responses = ["plan", [
            AgentEvent(AgentEventType.TEXT, {"content": "partial output"}),
            AgentEvent(AgentEventType.ERROR, {"error": "worker event failed"}),
        ], RuntimeError("fallback failed"), "approved"]
        with patch.object(agent_runner, "MAX_RETRIES", 0), patch.object(
            agent_runner, "_get_fallback_model", return_value=("openai", "test-fallback")
        ):
            await self.engine.run_task("task")
        await self.assert_failed("worker failed after retry")
        self.assertEqual(self.responses, ["approved"])


if __name__ == "__main__":
    unittest.main()
