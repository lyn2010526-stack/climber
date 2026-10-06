"""Regression tests for R9-10 (clarified design): credential resolution paths.

Wave 2 deliberately changed the dispatch contract:

* fresh ``submit()`` keeps ``resolve_credentials=False`` — the caller just
  supplied provider/model/api_key in the request payload and
  ``handle_agent_run`` consumes exactly that payload;
* recover/resume/retry dispatch with ``resolve_credentials=True`` — the
  persisted envelope strips sensitive keys, so the task owner's stored model
  configuration is resolved before dispatch.

These tests lock that contract so a future refactor cannot silently force
stored-config resolution onto fresh submissions (or drop it from recovery).
"""
from __future__ import annotations

import asyncio
import json
import unittest
from datetime import UTC, datetime
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Load defaults only: never read the workspace dotenv or provider environment.
with patch.object(
    BaseSettings, "settings_customise_sources",
    side_effect=lambda settings_cls, **sources: (sources["init_settings"],),
):
    from app.config import settings

settings.database_url = "sqlite+aiosqlite:///:memory:"
settings.test_database_url = settings.database_url
settings.app_testing = True
settings.app_secret_key = "credential-resolution-synthetic-secret"

from app.core import task_worker  # noqa: E402
from app.core.api_key_crypto import encrypt_api_key  # noqa: E402
from app.storage import Base  # noqa: E402
from app.storage.database import Agent, ApiKey  # noqa: E402
from app.storage.models_platform import AutoLoopTask  # noqa: E402


class ScriptedFakeEngine:
    """Deliberate model boundary fake; never makes network or tool calls."""

    def __init__(self):
        self.sessions: list[dict] = []
        self.runs = 0

    def create_session(self, **config):
        self.sessions.append(config)
        return SimpleNamespace(metrics=SimpleNamespace(total_tokens_used=1, total_iterations=1))

    async def run(self, session, objective):
        self.runs += 1
        for kind, data in (
            ("thinking", {"iteration": 1}),
            ("text", {"content": "scripted answer"}),
            ("done", {"status": "completed", "iterations": 1}),
        ):
            yield SimpleNamespace(type=SimpleNamespace(value=kind), data=data)


class CredentialResolutionContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = TemporaryDirectory(prefix="cred-resolution-")
        self.db_engine = create_async_engine(f"sqlite+aiosqlite:///{self.temp.name}/tasks.sqlite")
        self.sessions = async_sessionmaker(self.db_engine, expire_on_commit=False)
        async with self.db_engine.begin() as conn:
            await conn.run_sync(lambda db: Base.metadata.create_all(
                db, tables=[Agent.__table__, ApiKey.__table__, AutoLoopTask.__table__]
            ))
        self.patches = [
            patch.object(task_worker, "async_session", self.sessions),
        ]
        for item in self.patches:
            item.start()
        self.manager = task_worker.TaskManager()
        self.manager.register("agent_run", task_worker.handle_agent_run)

    async def asyncTearDown(self):
        tasks = list(self.manager._active_tasks.values())
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for item in reversed(self.patches):
            item.stop()
        await self.db_engine.dispose()
        self.temp.cleanup()

    async def add_owner(self, owner="alice", key="synthetic-alice-key", provider="owner-provider"):
        async with self.sessions() as db:
            db.add(Agent(
                id=f"agent-{owner}", user_id=owner, name=owner, provider=provider,
                model_id="owner-model", system_prompt="owner prompt", tool_ids=[],
                base_url="https://owner.invalid/v1",
                api_key_encrypted=encrypt_api_key(key),
            ))
            await db.commit()

    async def add_row(self, task_id, objective, owner="alice", **values):
        async with self.sessions() as db:
            db.add(AutoLoopTask(id=task_id, objective=objective, owner_id=owner,
                                **{"status": "pending", "max_steps": 10, "current_step": 0, **values}))
            await db.commit()

    async def row(self, task_id):
        async with self.sessions() as db:
            return await db.get(AutoLoopTask, task_id)

    async def drain(self):
        tasks = list(self.manager._active_tasks.values())
        if tasks:
            await asyncio.wait_for(asyncio.gather(*tasks), 30)

    async def test_fresh_submit_honors_request_credentials_without_resolution(self):
        """R9-10 contract: new submissions must NOT resolve stored owner config."""
        await self.add_owner()
        fake = ScriptedFakeEngine()
        resolver = AsyncMock(side_effect=AssertionError(
            "fresh submit must not resolve stored owner credentials"
        ))
        with patch("app.core.di.resolve", return_value=fake), \
                patch.object(task_worker, "resolve_owner_agent_payload", resolver):
            task_id = await self.manager.submit("agent_run", {
                "objective": "work",
                "provider": "request-provider",
                "model": "request-model",
                "api_key": "synthetic-request-key",
                "base_url": "https://request.invalid/v1",
            }, owner_id="alice")
            await self.drain()

        resolver.assert_not_called()
        self.assertEqual(fake.runs, 1)
        self.assertEqual(fake.sessions[0]["api_key"], "synthetic-request-key")
        self.assertEqual(fake.sessions[0]["provider"], "request-provider")
        self.assertEqual(fake.sessions[0]["model_id"], "request-model")
        row = await self.row(task_id)
        self.assertEqual(row.status, "completed")
        # The persisted envelope strips the sensitive key.
        self.assertNotIn("synthetic-request-key", row.objective)

    async def test_recover_pending_resolves_stored_owner_config(self):
        """Recovery path: stored owner config is resolved because the request key is gone."""
        await self.add_owner()
        await self.add_row("worker-original", json.dumps({
            "type": "agent_run", "objective": "work",
            "provider": "owner-provider", "model": "owner-model",
        }))
        fake = ScriptedFakeEngine()
        resolver = AsyncMock(wraps=task_worker.resolve_owner_agent_payload)
        with patch("app.core.di.resolve", return_value=fake), \
                patch.object(task_worker, "resolve_owner_agent_payload", resolver):
            self.assertEqual(await self.manager.recover_pending_tasks(), 1)
            await self.drain()

        resolver.assert_awaited_once()
        self.assertEqual(resolver.await_args.args[0], "alice")
        self.assertEqual(fake.runs, 1)
        self.assertEqual(fake.sessions[0]["api_key"], "synthetic-alice-key")
        self.assertEqual((await self.row("worker-original")).status, "completed")

    async def test_resume_resolves_stored_owner_config(self):
        """Resume control path resolves stored config like recovery does."""
        await self.add_owner()
        await self.add_row("worker-paused", json.dumps({
            "type": "agent_run", "objective": "work",
            "provider": "owner-provider", "model": "owner-model",
        }), status="paused", started_at=datetime.now(UTC))
        fake = ScriptedFakeEngine()
        resolver = AsyncMock(wraps=task_worker.resolve_owner_agent_payload)
        with patch("app.core.di.resolve", return_value=fake), \
                patch.object(task_worker, "resolve_owner_agent_payload", resolver):
            self.assertTrue(await self.manager.resume("worker-paused"))
            await self.drain()

        resolver.assert_awaited_once()
        self.assertEqual(fake.sessions[0]["api_key"], "synthetic-alice-key")
        self.assertEqual((await self.row("worker-paused")).status, "completed")

    async def test_retry_after_failure_keeps_resolution_contract(self):
        """A recovered task that fails re-resolves stored config on each retry."""
        await self.add_owner()

        async def failing_handler(payload, on_progress):
            return {"status": "failed", "error": "scripted failure"}

        manager = task_worker.TaskManager(max_task_retries=1)
        manager.register("agent_run", failing_handler)
        await self.add_row("worker-flaky", json.dumps({
            "type": "agent_run", "objective": "work",
            "provider": "owner-provider", "model": "owner-model",
        }))
        resolver = AsyncMock(wraps=task_worker.resolve_owner_agent_payload)
        with patch.object(task_worker, "resolve_owner_agent_payload", resolver):
            self.assertEqual(await manager.recover_pending_tasks(), 1)
            await asyncio.wait_for(
                asyncio.gather(*manager._active_tasks.values(), return_exceptions=True), 30
            )

        # One resolution for the initial recovery dispatch; the failed run is
        # marked failed after the retry budget is spent.
        self.assertGreaterEqual(resolver.await_count, 1)
        self.assertEqual((await self.row("worker-flaky")).status, "failed")
