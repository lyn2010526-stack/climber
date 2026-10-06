"""Real collaboration/engine/registry/SQLite with scripted provider responses.

No live provider requests. Dotenv loading and inherited environment are disabled.
Run directly with python3 -m unittest discover -s tests/isolated
-p test_collaboration_model_roles.py -v.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

with (
    patch.dict(
        os.environ,
        {
            "APP_TESTING": "true",
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "TEST_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        },
        clear=True,
    ),
    patch("dotenv.load_dotenv", return_value=False),
):
    from app.core import ChatResult
    from app.core.agent_engine import AgentEngine
    from app.core.collaboration import agent_runner, hierarchical, sequential
    from app.core.collaboration.prompts import parse_review_result
    from app.core.engine.run_storage import RunStorage
    from app.models.registry import PROVIDERS, ModelRegistry
    from app.storage import Base
    from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupTask

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "isolated_engine_audit"))
from test_runtime_persistence import RuntimePersistenceTests


class CollaborationModelRolesTests(RuntimePersistenceTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        async with self.db_engine.begin() as connection:
            await connection.run_sync(
                lambda conn: Base.metadata.create_all(
                    conn,
                    tables=[
                        AgentGroup.__table__,
                        AgentGroupMember.__table__,
                        AgentGroupTask.__table__,
                    ],
                )
            )
        for module in (hierarchical, sequential):
            self.enterContext(patch.object(module, "async_session", self.factory))
            self.enterContext(
                patch.object(module, "resolve_api_key", side_effect=lambda _p, k: k or "fake")
            )
            self.enterContext(
                patch.object(module, "resolve_base_url", return_value="https://scripted.invalid/v1")
            )
        self.enterContext(patch.object(hierarchical, "store_memory", new_callable=AsyncMock))
        self.enterContext(
            patch.object(hierarchical, "invoke_task_callback", new_callable=AsyncMock)
        )
        self.enterContext(
            patch.object(hierarchical, "invoke_step_callback", new_callable=AsyncMock)
        )
        self.broadcast = self.enterContext(
            patch.object(hierarchical.group_ws_hub, "broadcast", new_callable=AsyncMock)
        )
        self.enterContext(
            patch.object(sequential, "update_checkpoint_status", new_callable=AsyncMock)
        )
        self.calls = []
        self.responses = []
        calls, responses = self.calls, self.responses

        class ScriptedAdapter:
            def __init__(self, model_id, api_key, base_url=None):
                self.model_id, self.api_key, self.base_url = model_id, api_key, base_url
                self.capabilities = SimpleNamespace(streaming=False, max_tokens=100000)

            async def chat(adapter, messages, **_kwargs):
                calls.append((adapter, list(messages)))
                result = responses.pop(0)
                if isinstance(result, Exception):
                    raise result
                response = ChatResult(content=result, tokens_used=7)
                response.usage = {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7}
                return response

        self.enterContext(patch.dict(PROVIDERS, {"scripted": ScriptedAdapter}))
        self.registry = ModelRegistry()
        self.registry.register_model("high", "scripted", "cache-marker")
        self.enterContext(
            patch.object(
                agent_runner,
                "di_resolve",
                side_effect=lambda name: self.registry if name == "ModelRegistry" else Mock(),
            )
        )

        def engine_factory(**kwargs):
            engine = AgentEngine(**kwargs, run_store=RunStorage(self.factory))
            engine.permission_overlay = None
            engine.agent_mode = None
            self.engines.append(engine)
            return engine

        self.enterContext(patch.object(agent_runner, "AgentEngine", side_effect=engine_factory))

    async def fixtures(self, rounds=2, reviewer=True):
        members = [
            AgentGroupMember(
                id="planner",
                agent_id=None,
                role="planner",
                model_provider="scripted",
                model_id="high",
                api_key_encrypted="planner-marker",
            ),
            AgentGroupMember(
                id="worker",
                agent_id=None,
                role="executor",
                model_provider="scripted",
                model_id="low",
                api_key_encrypted="worker-marker",
            ),
        ]
        if reviewer:
            members.append(
                AgentGroupMember(
                    id="reviewer",
                    agent_id=None,
                    role="reviewer",
                    model_provider="scripted",
                    model_id="high",
                    api_key_encrypted="reviewer-marker",
                )
            )
        group = AgentGroup(id="group", name="roles", user_id="owner", members=members)
        task = AgentGroupTask(
            id="task",
            group_id="group",
            description="Produce artifact",
            max_rounds=rounds,
            worker_id="worker",
        )
        async with self.factory() as db:
            db.add_all([group, task])
            await db.commit()
        return group, task

    async def test_high_low_high_real_engine_binding(self):
        group, task = await self.fixtures()
        self.responses[:] = ["plan", "artifact", json.dumps({"passed": True, "issues": []})]
        await hierarchical.run_hierarchical_process(task, group)
        self.assertEqual([a.model_id for a, _ in self.calls], ["high", "low", "high"])
        self.assertEqual(
            [a.api_key for a, _ in self.calls],
            ["planner-marker", "worker-marker", "reviewer-marker"],
        )
        self.assertIsNot(self.calls[0][0], self.calls[2][0])
        self.assertEqual(self.registry.get_model("scripted", "high").api_key, "cache-marker")
        self.assertTrue(all(a.base_url == "https://scripted.invalid/v1" for a, _ in self.calls))
        self.assertTrue(
            all(s.user_id == "owner" for e in self.engines for s in e._sessions.values())
        )
        async with self.factory() as db:
            saved = await db.get(AgentGroupTask, task.id)
            self.assertEqual((saved.status, saved.final_output), ("completed", "artifact"))

    async def test_rejection_is_revised_with_bounded_feedback(self):
        group, task = await self.fixtures()
        self.responses[:] = [
            "plan",
            "draft",
            '{"passed":false,"issues":[{"description":"fix evidence"}]}',
            "revised",
            '{"passed":true,"issues":[]}',
        ]
        await hierarchical.run_hierarchical_process(task, group)
        self.assertEqual(
            [a.model_id for a, _ in self.calls], ["high", "low", "high", "low", "high"]
        )
        self.assertIn("fix evidence", str(self.calls[3][1]))
        self.assertIn("draft", str(self.calls[3][1]))
        async with self.factory() as db:
            saved = await db.get(AgentGroupTask, task.id)
            self.assertEqual((saved.status, saved.current_round), ("completed", 2))

    async def test_invalid_reviews_exhaust_limit_as_partial(self):
        group, task = await self.fixtures()
        self.responses[:] = ["plan", "draft", "不通过", "revised", "not approved"]
        await hierarchical.run_hierarchical_process(task, group)
        async with self.factory() as db:
            self.assertEqual((await db.get(AgentGroupTask, task.id)).status, "partial")
        self.assertEqual(len(self.calls), 5)

    async def test_review_exception_blocks_completion(self):
        group, task = await self.fixtures(rounds=1, reviewer=False)
        self.responses[:] = ["plan", "draft", RuntimeError("scripted failure")]
        with self.assertRaisesRegex(RuntimeError, "Manager validation failed"):
            await hierarchical.run_hierarchical_process(task, group)
        async with self.factory() as db:
            self.assertNotEqual((await db.get(AgentGroupTask, task.id)).status, "completed")

    async def test_sequential_review_is_fail_closed(self):
        group, task = await self.fixtures()
        reviewer = group.members[-1]
        for output in (
            "不通过",
            "not approved",
            '{"passed":false,"issues":[]}',
            RuntimeError("failure"),
        ):
            with self.subTest(output=str(output)):
                self.responses[:] = [output]
                issues = await sequential._execute_reviewer_turn(
                    task, [reviewer], "artifact", 7, agent_runner.principal_for_group(group)
                )
                self.assertTrue(issues)

    async def test_sequential_template_roles_revision_and_limit(self):
        group, task = await self.fixtures()
        self.enterContext(patch.object(sequential, "inject_memory", AsyncMock(return_value="")))
        self.enterContext(
            patch.object(sequential, "build_context_from_dependencies", AsyncMock(return_value={}))
        )
        self.enterContext(
            patch.object(sequential, "run_guardrails", AsyncMock(return_value=(True, [])))
        )
        self.enterContext(patch.object(sequential, "store_memory", new_callable=AsyncMock))
        self.enterContext(
            patch.object(sequential, "_checkpoint_and_broadcast", new_callable=AsyncMock)
        )
        self.responses[:] = [
            "draft",
            '{"passed":false,"issues":["fix evidence"]}',
            "revised",
            '{"passed":true,"issues":[]}',
        ]
        await sequential.run_sequential_process(task, group.members[0], [], group, 2)
        self.assertEqual([a.model_id for a, _ in self.calls], ["low", "high", "low", "high"])
        self.assertIn("fix evidence", str(self.calls[2][1]))
        async with self.factory() as db:
            self.assertEqual((await db.get(AgentGroupTask, task.id)).status, "completed")

    async def test_sequential_rejection_limit_is_partial(self):
        group, task = await self.fixtures(rounds=1)
        self.enterContext(patch.object(sequential, "inject_memory", AsyncMock(return_value="")))
        self.enterContext(
            patch.object(sequential, "build_context_from_dependencies", AsyncMock(return_value={}))
        )
        self.enterContext(
            patch.object(sequential, "run_guardrails", AsyncMock(return_value=(True, [])))
        )
        self.enterContext(
            patch.object(sequential, "_checkpoint_and_broadcast", new_callable=AsyncMock)
        )
        self.responses[:] = ["draft", "not approved"]
        await sequential.run_sequential_process(task, group.members[1], [], group, 1)
        async with self.factory() as db:
            self.assertEqual((await db.get(AgentGroupTask, task.id)).status, "partial")

    async def test_reviewer_timeout_blocks_sequential(self):
        group, task = await self.fixtures()
        with patch.object(agent_runner, "run_agent_simple", AsyncMock(side_effect=TimeoutError)):
            issues = await sequential._execute_reviewer_turn(
                task, [group.members[-1]], "draft", 7, agent_runner.principal_for_group(group)
            )
        self.assertTrue(issues)

    def test_strict_review_contract(self):
        for output in (
            "",
            "pass",
            "不通过",
            "not approved",
            "invalid",
            "{}",
            '{"passed":"true","issues":[]}',
            '{"passed":1,"issues":[]}',
            '{"passed":true,"issues":[{}]}',
            '{"passed":true,"issues":["fix"]}',
            '{"passed":false,"issues":[]}',
            '{"passed":true,"issues":[],"extra":1}',
        ):
            with self.subTest(output=output):
                passed, issues = parse_review_result(output)
                self.assertFalse(passed)
                self.assertTrue(issues)
        self.assertEqual(parse_review_result('{"passed":true,"issues":[]}'), (True, []))


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    for name in CollaborationModelRolesTests.__dict__:
        if name.startswith("test_"):
            suite.addTest(CollaborationModelRolesTests(name))
    suite.addTests(loader.loadTestsFromTestCase(RuntimePersistenceTests))
    return suite


if __name__ == "__main__":
    unittest.main()
