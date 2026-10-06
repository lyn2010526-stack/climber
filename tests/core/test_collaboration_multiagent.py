"""Multi-agent hardening tests for the collaboration layer.

Real: ORM models, sequential/group_chat/hierarchical processes, checkpoint
persistence, retry/fallback runner, principal resolution.
Replaced: session factories (temporary SQLite), run_agent (scripted events),
credential resolution, websocket transport and memory side effects.

Covers:
- checkpoint resume continues from the checkpoint round (not a restart)
- sequential worker failure persists the task as failed
- group_chat agent failure marks the task failed and is never spoken as a
  conversation message
- worker and reviewer agent calls receive an explicit principal derived from
  the group owner (no get_context_principal fallback dependency)
- engine._run_agent_with_retry forwards to agent_runner (single retry
  implementation, RuntimeError on exhaustion)

Run with pytest. No live LLM.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Isolate storage initialization as well as every session used by this suite.
with patch.dict(os.environ, {
    "APP_TESTING": "true",
    "TEST_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
}):
    from app.core import AgentEvent, AgentEventType
    from app.core.collaboration import (
        agent_runner,
        base,
        checkpoint,
        group_chat,
        hierarchical,
        sequential,
    )
    from app.storage import Base
    from app.storage.models_groups import (
        AgentGroup, AgentGroupMember, AgentGroupTask, AgentGroupTaskCheckpoint,
    )


class MultiAgentHardeningTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        directory = tempfile.TemporaryDirectory(prefix="collaboration-multiagent-")
        self.addCleanup(directory.cleanup)
        url = f"sqlite+aiosqlite:///{Path(directory.name) / 'tasks.db'}"
        self.db_engine = create_async_engine(url)
        self.addAsyncCleanup(self.db_engine.dispose)

        self.sessions = async_sessionmaker(self.db_engine, expire_on_commit=False)
        async with self.db_engine.begin() as connection:
            await connection.run_sync(
                Base.metadata.create_all,
                tables=[model.__table__ for model in (
                    AgentGroup, AgentGroupMember, AgentGroupTask, AgentGroupTaskCheckpoint,
                )],
            )
        for module in (base, sequential, group_chat, hierarchical, checkpoint):
            self.enterContext(patch.object(module, "async_session", self.sessions))
        self.broadcast = self.enterContext(
            patch.object(base.group_ws_hub, "broadcast", new_callable=AsyncMock)
        )
        for module in (base, sequential, group_chat, hierarchical):
            self.enterContext(patch.object(module, "resolve_api_key", return_value="test-only"))
            self.enterContext(patch.object(module, "resolve_base_url", return_value=None))
            self.enterContext(patch.object(module, "store_memory", new_callable=AsyncMock))
        self.enterContext(patch.object(base, "inject_memory", AsyncMock(return_value="")))
        self.enterContext(patch.object(sequential, "inject_memory", AsyncMock(return_value="")))

        self.calls = []
        self.responses = []

        async def scripted_agent(*args, **kwargs):
            self.calls.append({
                "agent_id": args[0],
                "principal": args[8] if len(args) > 8 else kwargs.get("principal"),
                "prompt": args[5],
            })
            response = self.responses.pop(0)
            if isinstance(response, BaseException):
                raise response
            if isinstance(response, list):
                for event in response:
                    yield event
                return
            yield AgentEvent(AgentEventType.TEXT, {"content": response})
            yield AgentEvent(AgentEventType.DONE, {"status": "completed", "tokens_used": 7})

        self.enterContext(patch.object(agent_runner, "run_agent", scripted_agent))
        self.engine = base.GroupCollaborationEngine(None, None)

    async def create_fixtures(self, process_type: str, with_reviewer: bool = False):
        worker = AgentGroupMember(
            id=f"{process_type}-worker", agent_id="worker-agent", role="worker",
        )
        group = AgentGroup(
            id=f"group-{process_type}", name="Multi-agent", process_type=process_type,
            user_id="owner-777", members=[worker],
        )
        task = AgentGroupTask(
            id=f"task-{process_type}", group_id=group.id, description="Do the thing",
            worker_id=worker.id, status="pending",
        )
        if with_reviewer:
            reviewer = AgentGroupMember(
                id=f"{process_type}-reviewer", agent_id="reviewer-agent", role="reviewer",
            )
            group.members.append(reviewer)
            task.reviewer_ids = [reviewer.id]
        async with self.sessions() as db:
            db.add_all([group, task])
            await db.commit()
        return group, task

    async def persisted_task(self):
        async with self.sessions() as db:
            return await db.get(AgentGroupTask, "task-" + (self._process_type or "sequential"))

    def events(self, kind):
        return [call.args[1]["data"] for call in self.broadcast.await_args_list
                if call.args[1]["type"] == kind]

    def assert_owner_principal(self, subject_id="owner-777"):
        for call in self.calls:
            self.assertIsNotNone(call["principal"], f"{call['agent_id']} missing principal")
            self.assertEqual(call["principal"].subject_id, subject_id)

    async def test_checkpoint_resume_continues_from_previous_round(self):
        self._process_type = "sequential"
        group, _task = await self.create_fixtures("sequential", with_reviewer=True)
        await checkpoint.save_checkpoint(
            "task-sequential",
            group.id,
            current_round=2,
            max_rounds=5,
            current_artifact="draft v2",
            all_issues=[{"description": "fix typo", "severity": "low"}],
            status="running",
        )
        self.responses = ["round3 revision", '{"passed":true,"issues":[]}']

        await self.engine.run_task("task-sequential")

        task = await self.persisted_task()
        self.assertEqual(task.status, "completed")
        self.assertEqual(task.current_round, 3)
        self.assertEqual(task.final_output, "round3 revision")
        self.assertEqual([call["agent_id"] for call in self.calls],
                         ["worker-agent", "reviewer-agent"])
        self.assertIn("draft v2", self.calls[0]["prompt"])
        self.assertIn("fix typo", self.calls[0]["prompt"])
        self.assertEqual(len(self.events("task_completed")), 1)
        self.assertEqual(self.events("task_failed"), [])
        self.assert_owner_principal()

    async def test_sequential_worker_failure_persists_failed(self):
        self._process_type = "sequential"
        await self.create_fixtures("sequential")
        self.responses = [RuntimeError("worker exploded")]
        with patch.object(agent_runner, "MAX_RETRIES", 0), patch.object(
            agent_runner, "_get_fallback_model", return_value=None
        ):
            await self.engine.run_task("task-sequential")

        task = await self.persisted_task()
        self.assertEqual(task.status, "failed")
        self.assertIsNone(task.final_output)
        failed_events = self.events("task_failed")
        self.assertEqual(len(failed_events), 1)
        self.assertIn("Worker failed after retry", failed_events[0]["error"])
        self.assertEqual(self.events("task_completed"), [])
        self.assertEqual(self.engine._running_tasks, {})

    async def test_group_chat_agent_failure_marks_task_failed(self):
        self._process_type = "group_chat"
        await self.create_fixtures("group_chat")
        self.responses = [RuntimeError("chat agent down")]

        await self.engine.run_task("task-group_chat")

        task = await self.persisted_task()
        self.assertEqual(task.status, "failed")
        failed_events = self.events("task_failed")
        self.assertEqual(len(failed_events), 1)
        self.assertIn("chat agent down", failed_events[0]["error"])
        self.assertEqual(self.events("task_completed"), [])
        self.assertEqual(self.events("message"), [])
        self.assert_owner_principal()

    async def test_dag_worker_and_reviewer_receive_group_owner_principal(self):
        self._process_type = "sequential"
        group, task = await self.create_fixtures("sequential", with_reviewer=True)
        self.responses = ["worker output", '{"passed":true,"issues":[]}']

        await self.engine._run_single_task_in_dag(task, group, {})

        task_row = await self.persisted_task()
        self.assertEqual(task_row.status, "completed")
        self.assertEqual(task_row.final_output, "worker output")
        self.assertEqual([call["agent_id"] for call in self.calls],
                         ["worker-agent", "reviewer-agent"])
        self.assert_owner_principal()
        self.assertEqual(self.events("task_failed"), [])

    async def test_dag_rejected_and_malformed_reviews_remain_partial(self):
        self._process_type = "sequential"
        group, task = await self.create_fixtures("sequential", with_reviewer=True)
        for review in ('{"passed":false,"issues":[{"description":"missing evidence"}]}',
                       '{"passed":false,"issues":[]}', "不通过", "not approved", ""):
            with self.subTest(review=review):
                self.broadcast.reset_mock()
                self.responses = ["worker draft", review]
                await self.engine._run_single_task_in_dag(task, group, {})
                saved = await self.persisted_task()
                self.assertEqual(saved.status, "partial")
                self.assertEqual(saved.final_output, "worker draft")
                self.assertEqual(self.events("task_completed"), [])
                self.assertTrue(self.events("task_partial")[0]["issues"])
                self.assert_owner_principal()

    async def test_dag_review_exception_persists_failed(self):
        self._process_type = "sequential"
        group, task = await self.create_fixtures("sequential", with_reviewer=True)
        self.responses = ["worker draft", RuntimeError("review unavailable")]
        with self.assertRaisesRegex(RuntimeError, "review unavailable"):
            await self.engine._run_single_task_in_dag(task, group, {})
        self.assertEqual((await self.persisted_task()).status, "failed")
        self.assertEqual(self.events("task_completed"), [])

    async def test_dag_approval_runs_dependent_task_with_worker_output(self):
        self._process_type = "sequential"
        group, task = await self.create_fixtures("sequential", with_reviewer=True)
        async with self.sessions() as db:
            db.add(AgentGroupTask(id="dependent", group_id=group.id, description="Use approved output",
                                 dependencies=[task.id], worker_id=task.worker_id, status="pending"))
            await db.commit()
        self.responses = ["approved worker output", '{"passed":true,"issues":[]}', "dependent output"]
        result = await self.engine.run_group_tasks(group.id)
        self.assertEqual(result["status"], "completed")
        self.assertEqual([level[0]["status"] for level in result["levels"]],
                         ["completed", "completed"])
        async with self.sessions() as db:
            dependent = await db.get(AgentGroupTask, "dependent")
            self.assertEqual(dependent.status, "completed")
            self.assertEqual(dependent.final_output, "dependent output")
        self.assertIn("approved worker output", self.calls[-1]["prompt"])
        self.assertEqual(len(self.events("task_completed")), 2)

    async def test_dag_rejection_blocks_dependent_task(self):
        self._process_type = "sequential"
        group, task = await self.create_fixtures("sequential", with_reviewer=True)
        async with self.sessions() as db:
            db.add(AgentGroupTask(id="dependent", group_id=group.id, description="Use approved output",
                                 dependencies=[task.id], worker_id=task.worker_id, status="pending"))
            await db.commit()
        self.responses = ["worker draft", '{"passed":false,"issues":[]}']
        result = await self.engine.run_group_tasks(group.id)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["levels"][0][0]["status"], "partial")
        self.assertEqual(result["levels"][1][0]["status"], "failed")
        async with self.sessions() as db:
            self.assertEqual((await db.get(AgentGroupTask, "dependent")).status, "failed")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.events("task_completed"), [])

    async def test_engine_retry_method_delegates_to_agent_runner(self):
        self._process_type = "sequential"
        await self.create_fixtures("sequential")
        self.responses = [RuntimeError("primary failed")]
        principal = agent_runner.Principal(subject_id="caller-999")
        with patch.object(agent_runner, "MAX_RETRIES", 0), patch.object(
            agent_runner, "_get_fallback_model", return_value=None
        ):
            with self.assertRaisesRegex(RuntimeError, "worker failed after retry"):
                await self.engine._run_agent_with_retry(
                    agent_id="worker-agent", provider="openai", model_id="gpt-4o",
                    api_key="test-only", system_prompt="worker", user_message="task",
                    tools=[], group_id="group-sequential", role="worker",
                    principal=principal,
                )
        self.assertEqual(len(self.calls), 1)
        self.assertIs(self.calls[0]["principal"], principal)

    async def test_hierarchical_worker_failure_propagates_to_failed_task(self):
        self._process_type = "hierarchical"
        manager = AgentGroupMember(
            id="hierarchical-manager", agent_id="manager-agent", role="manager",
        )
        worker = AgentGroupMember(
            id="hierarchical-worker", agent_id="worker-agent", role="worker",
        )
        group = AgentGroup(
            id="group-hierarchical", name="Multi-agent", process_type="hierarchical",
            user_id="owner-777", manager_agent_id=manager.id, members=[manager, worker],
        )
        task = AgentGroupTask(
            id="task-hierarchical", group_id=group.id, description="Do the thing",
            worker_id=worker.id, status="pending",
        )
        async with self.sessions() as db:
            db.add_all([group, task])
            await db.commit()

        self.responses = ["the plan", RuntimeError("worker exploded")]
        with patch.object(agent_runner, "MAX_RETRIES", 0), patch.object(
            agent_runner, "_get_fallback_model", return_value=None
        ):
            await self.engine.run_task("task-hierarchical")

        async with self.sessions() as db:
            task_row = await db.get(AgentGroupTask, "task-hierarchical")
        self.assertEqual(task_row.status, "failed")
        failed_events = self.events("task_failed")
        self.assertEqual(len(failed_events), 1)
        self.assertIn("worker failed after retry", failed_events[0]["error"])
        self.assertEqual(self.events("task_completed"), [])
        self.assert_owner_principal()


    async def test_sequential_run_registers_worker_and_reviewer_tree_nodes(self):
        from app.core.collaboration.progress import drop_task_tree, get_task_tree_snapshot

        self._process_type = "sequential"
        group, task = await self.create_fixtures("sequential", with_reviewer=True)
        self.addCleanup(drop_task_tree, group.id)
        self.responses = ["worker output", '{"passed":true,"issues":[]}']

        result = await self.engine.run_group_tasks(group.id)

        self.assertEqual(result["status"], "completed")
        snapshot = get_task_tree_snapshot(group.id)
        statuses = {n["task_name"]: n["status"] for n in snapshot["nodes"]}
        self.assertEqual(statuses["worker:worker-agent"], "completed")
        self.assertEqual(statuses["reviewer:reviewer-agent"], "completed")
        self.assertIn("Do the thing", [n["task_name"] for n in snapshot["nodes"]])


if __name__ == "__main__":
    unittest.main()
