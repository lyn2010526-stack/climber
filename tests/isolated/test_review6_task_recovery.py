"""Review 6: real temporary SQLite, scripted fake model, no lifespan/conftest.

Run: python3 -m unittest discover -s tests/isolated -p test_review6_task_recovery.py -v
"""
from __future__ import annotations

import ast
import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from datetime import UTC, datetime

from pydantic_settings import BaseSettings
from sqlalchemy import select
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
settings.app_secret_key = "review6-synthetic-encryption-secret"

from app.core import auto_loop, task_worker
from app.core.api_key_crypto import encrypt_api_key
from app.storage import Base
from app.storage.database import Agent, ApiKey
from app.storage.models_platform import AutoLoopTask

# Exercise the actual wiring function without importing app.main's router graph
# or starting either recovery loop or any application lifespan services.
source = Path(__file__).resolve().parents[2] / "app" / "main.py"
tree = ast.parse(source.read_text())
wire_node = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "_wire_auto_loop_runner")
namespace = {}
exec(compile(ast.Module(body=[wire_node], type_ignores=[]), str(source), "exec"), namespace)
wire_runner = namespace["_wire_auto_loop_runner"]


class ScriptedFakeEngine:
    """Deliberate model boundary fake; never makes network or tool calls."""

    def __init__(self, events=None, observer=None):
        self.events = events if events is not None else [
            ("thinking", {"iteration": 1}),
            ("text", {"content": "scripted answer"}),
            ("done", {"status": "completed", "iterations": 1}),
        ]
        self.observer = observer
        self.sessions = []
        self.runs = 0

    def create_session(self, **config):
        self.sessions.append(config)
        return SimpleNamespace(metrics=SimpleNamespace(total_tokens_used=7, total_iterations=1))

    async def run(self, session, objective):
        self.runs += 1
        for kind, data in self.events:
            if kind == "raise":
                raise TimeoutError(data["message"])
            yield SimpleNamespace(type=SimpleNamespace(value=kind), data=data)
            if self.observer:
                await self.observer(kind)


class Review6RecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = TemporaryDirectory(prefix="review6-")
        self.db_engine = create_async_engine(f"sqlite+aiosqlite:///{self.temp.name}/tasks.sqlite")
        self.sessions = async_sessionmaker(self.db_engine, expire_on_commit=False)
        async with self.db_engine.begin() as conn:
            await conn.run_sync(lambda db: Base.metadata.create_all(
                db, tables=[Agent.__table__, ApiKey.__table__, AutoLoopTask.__table__]
            ))
        self.patches = [
            patch.object(auto_loop, "async_session", self.sessions),
            patch.object(task_worker, "async_session", self.sessions),
        ]
        for item in self.patches:
            item.start()
        self.loop_engine = auto_loop.AutoLoopEngine()
        wire_runner(self.loop_engine)
        self.manager = task_worker.TaskManager()
        self.manager.register("agent_run", task_worker.handle_agent_run)
        self.manager.register("data_processing", task_worker.handle_data_processing)

    async def asyncTearDown(self):
        tasks = [record.asyncio_task for record in self.loop_engine._tasks.values()
                 if record.asyncio_task is not None]
        tasks.extend(self.manager._active_tasks.values())
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for item in reversed(self.patches):
            item.stop()
        await self.db_engine.dispose()
        self.temp.cleanup()

    async def add_owner(self, owner="alice", key="synthetic-alice-key", provider="owner-provider", agent_key=False):
        async with self.sessions() as db:
            db.add(Agent(
                id=f"agent-{owner}", user_id=owner, name=owner, provider=provider,
                model_id="owner-model", system_prompt="owner prompt", tool_ids=["calculator"],
                base_url="https://owner.invalid/v1",
                api_key_encrypted=encrypt_api_key(key) if agent_key and key else None,
            ))
            if key and not agent_key:
                db.add(ApiKey(user_id=owner, name="synthetic", provider=provider,
                              api_key_encrypted=encrypt_api_key(key), base_url="https://key.invalid/v1"))
            await db.commit()

    async def add_row(self, task_id, objective="do work", owner="alice", **values):
        async with self.sessions() as db:
            db.add(AutoLoopTask(id=task_id, objective=objective, owner_id=owner,
                                **{"status": "pending", "max_steps": 10, "current_step": 0, **values}))
            await db.commit()

    async def row(self, task_id):
        async with self.sessions() as db:
            return await db.get(AutoLoopTask, task_id)

    async def drain(self):
        tasks = [record.asyncio_task for record in self.loop_engine._tasks.values()
                 if record.asyncio_task is not None]
        tasks.extend(list(self.manager._active_tasks.values()))
        if tasks:
            await asyncio.wait_for(asyncio.gather(*tasks), 30)

    async def test_creation_owner_config_and_durable_progress(self):
        await self.add_owner()
        observed = []
        task_id = None

        async def observe(kind):
            if kind == "thinking":
                row = await self.row(task_id)
                observed.append((row.status, row.current_step, row.max_steps, row.heartbeat_at is not None))

        fake = ScriptedFakeEngine(observer=observe)
        with patch("app.core.di.resolve", return_value=fake):
            task_id = self.loop_engine.start_task("do work", owner_id="alice")
            await self.drain()
        row = await self.row(task_id)
        self.assertEqual((row.owner_id, row.status, row.current_step, row.max_steps),
                         ("alice", "completed", 1, 10))
        self.assertEqual(observed, [("running", 1, 10, True)])
        self.assertIsNotNone(row.finished_at)
        self.assertEqual(row.result["output"], "scripted answer")
        self.assertEqual(fake.sessions[0]["user_id"], "alice")
        self.assertEqual(fake.sessions[0]["provider"], "owner-provider")
        self.assertEqual(fake.sessions[0]["model_id"], "owner-model")
        self.assertTrue(fake.sessions[0]["api_key"] == "synthetic-alice-key")
        self.assertEqual(fake.sessions[0]["base_url"], "https://key.invalid/v1")
        self.assertEqual(fake.sessions[0]["tools"], ["calculator"])
        self.assertNotIn("synthetic-alice-key", json.dumps(row.result))

    async def test_missing_owner_rejected_before_creation(self):
        with self.assertRaises(ValueError):
            self.loop_engine.start_task("do work", owner_id="")
        with self.assertRaises(TypeError):
            self.loop_engine.start_task("do work")

    async def test_reserved_envelope_rejected_at_auto_creation(self):
        with self.assertRaises(ValueError):
            self.loop_engine.start_task('{"type":"agent_run"}', owner_id="alice")

    async def test_no_credentials_never_uses_other_owner(self):
        await self.add_owner(key=None)
        await self.add_owner("bob", "synthetic-bob-key")
        fake = ScriptedFakeEngine()
        with patch("app.core.di.resolve", return_value=fake):
            task_id = self.loop_engine.start_task("do work", owner_id="alice")
            await self.drain()
        self.assertEqual((await self.row(task_id)).status, "failed")
        self.assertEqual(fake.sessions, [])
        with self.assertRaisesRegex(ValueError, "configuration"):
            await task_worker.resolve_owner_agent_payload("unknown-owner")

    async def test_inactive_and_wrong_provider_keys_are_ignored(self):
        await self.add_owner(key=None)
        async with self.sessions() as db:
            db.add_all([
                ApiKey(user_id="alice", name="inactive", provider="owner-provider",
                       api_key_encrypted=encrypt_api_key("synthetic-inactive"), is_active=False),
                ApiKey(user_id="alice", name="wrong-provider", provider="other",
                       api_key_encrypted=encrypt_api_key("synthetic-wrong-provider")),
            ])
            await db.commit()
        with self.assertRaisesRegex(ValueError, "credential"):
            await task_worker.resolve_owner_agent_payload("alice")

    async def test_agent_credential_and_corrupt_ciphertext(self):
        await self.add_owner(agent_key=True)
        payload = await task_worker.resolve_owner_agent_payload("alice")
        self.assertTrue(payload["api_key"] == "synthetic-alice-key")
        async with self.sessions() as db:
            agent = await db.get(Agent, "agent-alice")
            agent.api_key_encrypted = "enc:v1:synthetic-invalid"
            await db.commit()
        with self.assertRaisesRegex(ValueError, "cannot be decrypted"):
            await task_worker.resolve_owner_agent_payload("alice")

    async def test_pending_recovery_preserves_owner_id_and_skips_taskmanager(self):
        await self.add_owner()
        await self.add_row("auto-pending")
        await self.add_row("worker-pending", '{"type":"agent_run","objective":"worker"}')
        fake = ScriptedFakeEngine()
        with patch("app.core.di.resolve", return_value=fake):
            self.assertEqual(await self.loop_engine.recover_interrupted_sessions(), 1)
            await self.drain()
            self.assertEqual(await self.loop_engine.recover_interrupted_sessions(), 0)
        self.assertEqual(fake.runs, 1)
        row = await self.row("auto-pending")
        self.assertEqual((row.id, row.owner_id, row.status), ("auto-pending", "alice", "completed"))
        self.assertEqual((await self.row("worker-pending")).status, "pending")

    async def test_interrupted_and_ownerless_auto_rows_fail_without_replay(self):
        for status in ("running", "retrying"):
            await self.add_row(status, status=status)
        await self.add_row("started-pending", started_at=datetime.now(UTC))
        await self.add_row("progress-pending", current_step=1)
        await self.add_row("ownerless", owner="")
        fake = ScriptedFakeEngine()
        with patch("app.core.di.resolve", return_value=fake):
            await self.loop_engine.recover_interrupted_sessions()
            await self.drain()
        for task_id in ("running", "retrying", "started-pending", "progress-pending", "ownerless"):
            row = await self.row(task_id)
            self.assertEqual(row.status, "failed")
            self.assertIn("manual review", row.error)
        self.assertEqual(fake.runs, 0)

    async def test_error_missing_done_and_unsuccessful_done_never_complete(self):
        await self.add_owner()
        scripts = [
            [("thinking", {"iteration": 2}), ("error", {"error": "synthetic-alice-key"})],
            [("text", {"content": "partial"})],
            [("done", {"status": "max_iterations_reached", "iterations": 10})],
            [("done", {"status": "cancelled"})],
            [("raise", {"message": "timeout synthetic-alice-key"})],
        ]
        for script in scripts:
            with self.subTest(script=script[0][0]):
                fake = ScriptedFakeEngine(script)
                with patch("app.core.di.resolve", return_value=fake):
                    task_id = self.loop_engine.start_task("do work", owner_id="alice")
                    await self.drain()
                    await self.loop_engine.run_pending()
                    await self.drain()
                row = await self.row(task_id)
                self.assertEqual(row.status, "failed")
                self.assertIsNone(row.result)
                self.assertNotIn("synthetic-alice-key", row.error)
                self.assertEqual(fake.runs, 1)

    async def test_no_runner_and_placeholder_cannot_complete(self):
        self.loop_engine._runners.clear()
        first = self.loop_engine.start_task("do work", owner_id="alice")
        await self.drain()
        self.assertEqual((await self.row(first)).status, "failed")
        self.loop_engine.register_runner("autonomous", AsyncMock())
        second = self.loop_engine.start_task("do work", owner_id="alice")
        await self.drain()
        self.assertEqual((await self.row(second)).status, "failed")

    async def test_progress_handler_keeps_budget_and_done_content(self):
        fake = ScriptedFakeEngine([
            ("thinking", {"iteration": 2}),
            ("done", {"status": "completed", "iterations": 2, "content": "final only"}),
        ])
        progress = AsyncMock()
        with patch("app.core.di.resolve", return_value=fake):
            result = await task_worker.handle_agent_run({"objective": "work", "max_steps": 10}, progress)
        self.assertEqual(result["output"], "final only")
        self.assertEqual(progress.await_args_list[-1].args, (2, 10, "Complete"))

    async def test_worker_submit_preserves_owner_key_and_progress(self):
        fake = ScriptedFakeEngine()
        with patch("app.core.di.resolve", return_value=fake):
            task_id = await self.manager.submit("agent_run", {
                "objective": "work", "api_key": "synthetic-request-key", "user_id": "bob",
            }, owner_id="alice")
            await self.drain()
        row = await self.row(task_id)
        self.assertEqual((row.owner_id, row.status, row.current_step, row.max_steps),
                         ("alice", "completed", 1, 10))
        self.assertTrue(fake.sessions[0]["api_key"] == "synthetic-request-key")
        self.assertEqual(fake.sessions[0]["user_id"], "alice")
        self.assertNotIn("synthetic-request-key", row.objective)
        self.assertIsNone(await self.manager.get_status(task_id, owner_id="bob"))

    async def test_standalone_restores_same_id_owner_and_stored_key(self):
        await self.add_owner()
        await self.add_row("worker-original", json.dumps({
            "type": "agent_run", "objective": "work", "user_id": "bob",
            "provider": "owner-provider", "model": "owner-model",
            "api_key": "synthetic-stale-key", "base_url": "https://stale.invalid/v1",
        }))
        await self.add_row("auto-untouched")
        fake = ScriptedFakeEngine()
        with patch("app.core.di.resolve", return_value=fake):
            self.assertEqual(await self.manager.recover_pending_tasks(), 1)
            await self.drain()
            self.assertEqual(await self.manager.recover_pending_tasks(), 0)
        self.assertEqual(fake.runs, 1)
        self.assertTrue(fake.sessions[0]["api_key"] == "synthetic-alice-key")
        self.assertEqual(fake.sessions[0]["user_id"], "alice")
        self.assertEqual(fake.sessions[0]["base_url"], "https://key.invalid/v1")
        row = await self.row("worker-original")
        self.assertEqual((row.owner_id, row.status), ("alice", "completed"))
        async with self.sessions() as db:
            ids = set(await db.scalars(select(AutoLoopTask.id)))
        self.assertEqual(ids, {"worker-original", "auto-untouched"})
        self.assertEqual((await self.row("auto-untouched")).status, "pending")

    async def test_standalone_missing_credentials_fails_once(self):
        await self.add_owner(key=None)
        await self.add_owner("bob", "synthetic-bob-key")
        await self.add_row("worker-no-key", '{"type":"agent_run","objective":"work"}')
        fake = ScriptedFakeEngine()
        with patch("app.core.di.resolve", return_value=fake):
            await self.manager.recover_pending_tasks()
            await self.drain()
            self.assertEqual(await self.manager.recover_pending_tasks(), 0)
        self.assertEqual((await self.row("worker-no-key")).status, "failed")
        self.assertEqual(fake.runs, 0)

    async def test_standalone_leaves_running_and_rejects_started_pending(self):
        envelope = '{"type":"data_processing","data":["a"]}'
        await self.add_row("worker-running", envelope, status="running")
        await self.add_row("worker-retrying", envelope, status="retrying")
        await self.add_row("worker-started", envelope, started_at=datetime.now(UTC))
        await self.add_row("worker-ownerless", envelope, owner="")
        await self.add_row("worker-unknown", '{"type":"missing-handler"}')
        self.assertEqual(await self.manager.recover_pending_tasks(), 0)
        self.assertEqual((await self.row("worker-running")).status, "running")
        self.assertEqual((await self.row("worker-retrying")).status, "retrying")
        for task_id in ("worker-started", "worker-ownerless", "worker-unknown"):
            self.assertEqual((await self.row(task_id)).status, "failed")

    async def test_two_inprocess_claimants_execute_once(self):
        await self.add_row("claim-once", '{"type":"data_processing","data":["a"]}')
        calls = []

        async def handler(payload, on_progress):
            calls.append(payload["_task_id"])
            return {"output": "scripted"}

        self.manager.register("data_processing", handler)
        other = task_worker.TaskManager()
        other.register("data_processing", handler)
        await asyncio.gather(
            self.manager._run_task("claim-once", "data_processing", {}),
            other._run_task("claim-once", "data_processing", {}),
        )
        self.assertEqual(calls, ["claim-once"])

    async def test_factory_side_effect_step_is_not_retried(self):
        calls = []

        async def scripted_handler(payload, on_progress):
            calls.append(payload["tools"])
            if len(calls) == 1:
                return {"output": '{"steps":[{"action":"write","objective":"write once","tools":["write_file"]}]}'}
            raise TimeoutError("synthetic step failed after write")

        self.manager.register("agent_run", scripted_handler)
        with patch.object(task_worker, "task_manager", self.manager):
            with self.assertRaisesRegex(RuntimeError, "Factory step 1 failed"):
                await task_worker.handle_factory_run({
                    "_task_id": "factory", "objective": "write once",
                    "factory_skills": ["file_manager"], "tools": ["write_file"],
                }, AsyncMock())
        self.assertEqual(calls, [[], ["write_file"]])
        self.assertNotIn("task_retry", [e["type"] for e in self.manager._event_history["factory"]])

    async def test_auto_claim_failure_never_runs_model(self):
        fake = ScriptedFakeEngine()
        with patch("app.core.di.resolve", return_value=fake), patch.object(
            self.loop_engine, "_persist_status", AsyncMock(side_effect=RuntimeError("synthetic DB failure"))
        ):
            task_id = self.loop_engine.start_task("work", owner_id="alice")
            await self.drain()
        self.assertEqual(fake.runs, 0)
        self.assertEqual(self.loop_engine._tasks[task_id].status, auto_loop.AutoLoopTaskStatus.FAILED)
        self.assertIsNone(await self.row(task_id))

    async def test_auto_two_inprocess_claimants_execute_once(self):
        await self.add_owner()
        await self.add_row("auto-claim-once")
        other = auto_loop.AutoLoopEngine()
        wire_runner(other)
        records = [auto_loop.AutoLoopRecord(
            task_id="auto-claim-once", objective="do work", owner_id="alice"
        ) for _ in range(2)]
        fake = ScriptedFakeEngine()
        with patch("app.core.di.resolve", return_value=fake):
            await asyncio.gather(self.loop_engine._execute_task(records[0]), other._execute_task(records[1]))
        self.assertEqual(fake.runs, 1)
        self.assertEqual((await self.row("auto-claim-once")).status, "completed")

    async def test_auto_shutdown_cancels_without_replay(self):
        started = asyncio.Event()

        async def blocked_runner(record):
            started.set()
            await asyncio.Event().wait()

        self.loop_engine.register_runner("autonomous", blocked_runner)
        task_id = self.loop_engine.start_task("work", owner_id="alice")
        await asyncio.wait_for(started.wait(), 5)
        await self.loop_engine.stop()
        row = await self.row(task_id)
        self.assertEqual(row.status, "cancelled")
        self.assertIsNotNone(row.finished_at)
        self.assertEqual(await auto_loop.AutoLoopEngine().recover_interrupted_sessions(), 0)

    async def test_worker_cancel_and_error_callbacks(self):
        started = asyncio.Event()
        progress = []

        async def callback(task_id, data):
            progress.append(data)

        async def blocked_handler(payload, on_progress):
            await on_progress(2, 10, "scripted progress")
            started.set()
            await asyncio.Event().wait()

        self.manager.on_progress(callback)
        self.manager.register("agent_run", blocked_handler)
        task_id = await self.manager.submit("agent_run", {"objective": "work"}, owner_id="alice")
        await asyncio.wait_for(started.wait(), 5)
        await self.manager.cancel(task_id)
        await self.drain()
        row = await self.row(task_id)
        self.assertEqual((row.status, row.current_step, row.max_steps), ("cancelled", 2, 10))
        self.assertIn({"status": "cancelled"}, progress)
        self.manager.register("agent_run", task_worker.handle_agent_run)
        fake = ScriptedFakeEngine([("error", {"error": "synthetic-secret"})])
        with patch("app.core.di.resolve", return_value=fake):
            failed_id = await self.manager.submit("agent_run", {"objective": "work"}, owner_id="alice")
            await self.drain()
        self.assertEqual((await self.row(failed_id)).status, "failed")
        self.assertEqual(progress[-1]["status"], "failed")
        self.assertNotIn("synthetic-secret", json.dumps(progress))

    async def test_worker_claim_ignores_auto_rows(self):
        await self.add_row("auto-row")
        handler = AsyncMock()
        self.manager.register("agent_run", handler)
        await self.manager._run_task("auto-row", "agent_run", {})
        handler.assert_not_awaited()
        self.assertEqual((await self.row("auto-row")).status, "pending")

    async def test_owner_configured_local_model_runs_without_key(self):
        await self.add_owner(key=None, provider="ollama")
        fake = ScriptedFakeEngine()
        with patch("app.core.di.resolve", return_value=fake):
            task_id = self.loop_engine.start_task("work", owner_id="alice")
            await self.drain()
        self.assertEqual((await self.row(task_id)).status, "completed")
        self.assertEqual(fake.sessions[0]["api_key"], "")
        self.assertEqual(fake.sessions[0]["base_url"], "https://owner.invalid/v1")

    async def test_pending_worker_uses_explicit_model_with_owner_key(self):
        await self.add_owner()
        # A persisted model selection can outlive its Agent row. Its provider
        # credential must still come from the matching owner's active ApiKey.
        payload = await task_worker.resolve_owner_agent_payload("alice", {
            "provider": "owner-provider", "model": "explicit-model",
            "user_id": "bob", "api_key": "synthetic-wrong-key",
        })
        self.assertEqual(payload["model"], "explicit-model")
        self.assertEqual(payload["user_id"], "alice")
        self.assertTrue(payload["api_key"] == "synthetic-alice-key")


if __name__ == "__main__":
    unittest.main()
