"""Isolated regressions for task ownership and workflow run input contracts.

Run with unittest discovery for this file only; never load tests/conftest.py.
Authentication identities and workflow execution are test doubles. Task storage,
scope dependencies, HTTP request validation and cancellation are real.
"""

from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings

# Keep import-time storage initialization away from the shared database as well.
with (
    patch.object(settings, "database_url", "sqlite+aiosqlite:///:memory:"),
    patch.object(settings, "test_database_url", "sqlite+aiosqlite:///:memory:"),
):
    from app.api.v1.routes import tasks, workflows
    from app.core import task_worker
    from app.core.principal import (
        principal_from_auth,
        reset_current_principal,
        set_current_principal,
    )
    from app.storage.models_platform import AutoLoopTask


class TaskOwnerContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.addAsyncCleanup(self.engine.dispose)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(AutoLoopTask.__table__.create)
        self.manager = task_worker.TaskManager()
        self.enterContext(patch.object(task_worker, "async_session", self.sessions))
        self.enterContext(patch.object(tasks, "task_manager", self.manager))
        self.app = FastAPI()
        self.app.include_router(tasks.router, prefix="/api/v1")
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://test"
        )
        self.addAsyncCleanup(self.client.aclose)

    async def seed_task(self, owner="owner-a", active=True):
        task_id = "task-under-test"
        async with self.sessions() as session:
            session.add(AutoLoopTask(
                id=task_id, owner_id=owner, objective="contract test",
                status="running" if active else "completed",
            ))
            await session.commit()
        if active:
            worker = asyncio.create_task(asyncio.Event().wait())
            self.manager._active_tasks[task_id] = worker

            async def stop_worker():
                worker.cancel()
                await asyncio.gather(worker, return_exceptions=True)

            self.addAsyncCleanup(stop_worker)
        return task_id

    async def cancel(self, task_id, *, user="owner-a", scopes=("read", "write"), role="user", local=False):
        token = set_current_principal(principal_from_auth({
            "user_id": user, "scopes": scopes, "role": role, "method": "test",
        }))
        try:
            with patch.object(settings, "enable_auth", not local):
                return await self.client.post(f"/api/v1/tasks/{task_id}/cancel")
        finally:
            reset_current_principal(token)

    async def assert_status(self, task_id, expected):
        async with self.sessions() as session:
            record = await session.get(AutoLoopTask, task_id)
            self.assertEqual(record.status, expected)

    async def test_default_user_can_cancel_own_task_without_auth(self):
        task_id = await self.seed_task(owner="default-user")
        with patch.object(settings, "enable_auth", False):
            response = await self.client.post(f"/api/v1/tasks/{task_id}/cancel")
        self.assertEqual(response.status_code, 200, response.text)
        await self.assert_status(task_id, "cancelled")
        self.assertTrue(self.manager._active_tasks[task_id].cancelling())

    async def test_authenticated_owner_can_cancel_own_task(self):
        task_id = await self.seed_task()
        response = await self.cancel(task_id)
        self.assertEqual(response.status_code, 200, response.text)
        await self.assert_status(task_id, "cancelled")

    async def test_other_user_cannot_cancel_or_mutate_task(self):
        task_id = await self.seed_task()
        response = await self.cancel(task_id, user="owner-b")
        self.assertEqual(response.status_code, 404, response.text)
        await self.assert_status(task_id, "running")
        self.assertFalse(self.manager._active_tasks[task_id].cancelling())

    async def test_default_user_cannot_cancel_another_owner_in_local_mode(self):
        task_id = await self.seed_task()
        response = await self.cancel(task_id, user="default-user", scopes=(), local=True)
        self.assertEqual(response.status_code, 404, response.text)
        await self.assert_status(task_id, "running")
        self.assertFalse(self.manager._active_tasks[task_id].cancelling())

    async def test_read_only_owner_still_requires_write_scope(self):
        task_id = await self.seed_task()
        response = await self.cancel(task_id, scopes=("read",))
        self.assertEqual(response.status_code, 403, response.text)
        await self.assert_status(task_id, "running")

    async def test_admin_role_can_cancel_another_owner(self):
        task_id = await self.seed_task()
        response = await self.cancel(task_id, user="admin-user", scopes=(), role="admin")
        self.assertEqual(response.status_code, 200, response.text)
        await self.assert_status(task_id, "cancelled")

    async def test_admin_scope_can_cancel_another_owner(self):
        task_id = await self.seed_task()
        response = await self.cancel(task_id, user="admin-key", scopes=("admin",))
        self.assertEqual(response.status_code, 200, response.text)
        await self.assert_status(task_id, "cancelled")

    async def test_missing_task_returns_404(self):
        response = await self.cancel("missing")
        self.assertEqual(response.status_code, 404, response.text)

    async def test_completed_task_returns_400_and_stays_completed(self):
        task_id = await self.seed_task(active=False)
        response = await self.cancel(task_id)
        self.assertEqual(response.status_code, 400, response.text)
        await self.assert_status(task_id, "completed")

    async def test_missing_authenticated_principal_returns_401(self):
        task_id = await self.seed_task()
        with patch.object(settings, "enable_auth", True):
            response = await self.client.post(f"/api/v1/tasks/{task_id}/cancel")
        self.assertEqual(response.status_code, 401, response.text)
        await self.assert_status(task_id, "running")


class WorkflowInputContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.enterContext(patch.object(settings, "enable_auth", False))
        self.app = FastAPI()
        self.app.include_router(workflows.router, prefix="/api/v1")
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://test"
        )
        self.addAsyncCleanup(self.client.aclose)
        self.workflow = SimpleNamespace(
            id="wf", name="Contract", nodes=[{"id": "input", "type": "input"}], edges=[],
        )
        self.visible = self.enterContext(patch.object(
            workflows, "_visible_workflow", AsyncMock(return_value=self.workflow)
        ))
        self.session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = SimpleNamespace(id="agent")
        self.session.execute.return_value = result
        self.session_factory = self.enterContext(patch.object(workflows, "async_session"))
        self.session_factory.return_value.__aenter__.return_value = self.session
        self.execute = self.enterContext(patch.object(
            workflows, "_execute_workflow", AsyncMock(return_value={
                "status": "completed", "outputs": {},
            })
        ))
        self.record = self.enterContext(patch.object(workflows, "_record_workflow_run", AsyncMock()))

    async def test_inputs_envelope_reaches_execution_and_history_unchanged(self):
        inputs = {"question": "hello", "count": 0, "enabled": False, "nested": {"x": [1, 2]}}
        response = await self.client.post("/api/v1/workflows/wf/run", json={"inputs": inputs})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.execute.await_args.args[4]["inputs"], inputs)
        self.assertEqual(self.record.await_args.args[0].inputs, inputs)

    async def test_editor_empty_inputs_envelope_is_valid(self):
        response = await self.client.post("/api/v1/workflows/wf/run", json={"inputs": {}})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.execute.await_args.args[4]["inputs"], {})

    async def test_omitted_inputs_retains_declared_empty_default(self):
        response = await self.client.post("/api/v1/workflows/wf/run", json={})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.execute.await_args.args[4]["inputs"], {})

    async def test_flat_inputs_and_unknown_fields_return_explicit_422(self):
        for body in ({"question": "hello"}, {"inputs": {}, "unexpected": True}):
            with self.subTest(body=body):
                response = await self.client.post("/api/v1/workflows/wf/run", json=body)
                self.assertEqual(response.status_code, 422, response.text)
                self.assertTrue(any(error["type"] == "extra_forbidden" for error in response.json()["detail"]))
        self.session_factory.assert_not_called()
        self.execute.assert_not_awaited()

    async def test_non_object_inputs_return_explicit_422(self):
        for inputs in (None, [], ["x"], "text", 42, False):
            with self.subTest(inputs=inputs):
                response = await self.client.post("/api/v1/workflows/wf/run", json={"inputs": inputs})
                self.assertEqual(response.status_code, 422, response.text)
                self.assertTrue(any(error["loc"] == ["body", "inputs"] for error in response.json()["detail"]))
        self.session_factory.assert_not_called()
        self.execute.assert_not_awaited()

    async def test_non_object_body_and_malformed_json_return_422(self):
        for body in ("[]", "null", '"text"', "{"):
            with self.subTest(body=body):
                response = await self.client.post(
                    "/api/v1/workflows/wf/run", content=body, headers={"Content-Type": "application/json"},
                )
                self.assertEqual(response.status_code, 422, response.text)
        self.session_factory.assert_not_called()
        self.execute.assert_not_awaited()

    async def test_empty_graph_keeps_clear_422(self):
        self.workflow.nodes = []
        response = await self.client.post("/api/v1/workflows/wf/run", json={"inputs": {}})
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["detail"], "Workflow has no nodes to execute")
        self.execute.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
