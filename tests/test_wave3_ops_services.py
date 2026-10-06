"""Targeted regression tests for the wave-3 ops/services fixes.

Self-contained unittest module; does not depend on the shared pytest
fixtures so it can run standalone with `python -m pytest`.
"""
from __future__ import annotations

import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.execution.event_bus import EventBus, TaskEvent
from app.core.watchdog import INITIAL_BACKOFF, SupervisedTask, Watchdog
from app.main import SHUTDOWN_STEP_TIMEOUT, _run_cleanup_step
from app.services.notifications import NotificationService, compute_delivery_availability
from app.services.settings_service import SettingsService
from app.skills.package_manager import get_skill_manager
from app.storage import Base, _schema_ready
from app.storage.models_platform import UserSettings
from app.utils.notifications import _escape_applescript, _escape_powershell


class PackageManagerSingletonTest(unittest.TestCase):
    def test_get_skill_manager_returns_same_instance(self):
        self.assertIs(get_skill_manager(), get_skill_manager())


# SchedulerNoHandlerTest was removed in the 2026-10-05 dead-code cleanup:
# it covered app.core.scheduler.TaskScheduler, whose only wiring (main.py
# watchdog loop + DI registration) was removed together with that module's
# runtime usage.


class OllamaQueueNoCallbackTest(unittest.IsolatedAsyncioTestCase):
    async def test_no_callback_request_is_executed_not_dropped(self):
        from app.services import ollama_queue as ollama_module
        from app.services.ollama_queue import OllamaOfflineQueue, QueuedRequest

        queue = OllamaOfflineQueue()
        queue._queue.append(QueuedRequest(request_id="r1", payload={}))
        executed = []
        queue._execute_payload = lambda req: _record(executed, req)
        queue._ollama_online = True
        queue._last_check = time.time()
        with patch.object(ollama_module.logger, "info"), patch.object(ollama_module.logger, "warning"):
            await queue.process_queue()

        self.assertEqual(executed, ["r1"])
        self.assertEqual(queue.queue_size, 0)


async def _record(bucket, req):
    bucket.append(req.request_id)


class SettingsServiceInjectionTest(unittest.IsolatedAsyncioTestCase):
    async def _engine(self):
        tmp = tempfile.TemporaryDirectory(prefix="wave3-settings-", dir="/tmp/opencode")
        self.addCleanup(tmp.cleanup)
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp.name}/s.db")
        self.addAsyncCleanup(engine.dispose)
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=[UserSettings.__table__]))
        return engine

    async def test_uses_injected_db_and_get_or_creates(self):
        engine = await self._engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as db:
            service = SettingsService(db)
            settings = await service.get_settings("alice")
            self.assertEqual(settings.notifications.get("webhook_configured"), False)
        async with sessions() as db:
            row = (
                await db.execute(
                    __import__("sqlalchemy").select(UserSettings).where(UserSettings.user_id == "alice")
                )
            ).scalar_one_or_none()
            self.assertIsNotNone(row)

    async def test_falls_back_to_module_session_without_injection(self):
        engine = await self._engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        with patch("app.services.settings_service.async_session", sessions):
            service = SettingsService()
            await service.get_settings("bob")
        async with sessions() as db:
            row = (
                await db.execute(
                    __import__("sqlalchemy").select(UserSettings).where(UserSettings.user_id == "bob")
                )
            ).scalar_one_or_none()
            self.assertIsNotNone(row)


class NotificationEscapingTest(unittest.TestCase):
    def test_applescript_escapes_quotes_and_backslashes(self):
        self.assertEqual(_escape_applescript('say "hi" \\ now'), 'say \\"hi\\" \\\\ now')

    def test_powershell_escapes_single_quotes(self):
        self.assertEqual(_escape_powershell("it's a test"), "it''s a test")


class WatchdogBackoffTest(unittest.IsolatedAsyncioTestCase):
    async def test_alive_task_resets_backoff(self):
        watchdog = Watchdog()
        supervised = SupervisedTask(name="a", factory=_never)
        supervised.backoff = 8.0
        supervised.task = _FakeTask(alive=True)
        watchdog._tasks["a"] = supervised

        await watchdog.check_now()
        self.assertEqual(supervised.backoff, INITIAL_BACKOFF)

    async def test_backoff_is_gated_not_serial(self):
        watchdog = Watchdog()
        supervised = SupervisedTask(name="a", factory=_never, crashed=True)
        supervised.next_restart_at = time.time() + 1000
        watchdog._tasks["a"] = supervised

        start = time.monotonic()
        await watchdog.check_now()
        self.assertLess(time.monotonic() - start, 1.0)
        self.assertEqual(supervised.restarts, 0)


class _FakeTask:
    def __init__(self, alive):
        self._alive = alive

    def done(self):
        return not self._alive


async def _never():
    while True:
        await asyncio.sleep(3600)


class WatchdogHealthTest(unittest.TestCase):
    def test_all_stopped_is_not_healthy(self):
        watchdog = Watchdog()
        supervised = SupervisedTask(name="a", factory=_never)
        supervised.stopped = True
        watchdog._tasks["a"] = supervised
        self.assertFalse(watchdog.health()["healthy"])

    def test_empty_watchdog_is_healthy(self):
        self.assertTrue(Watchdog().health()["healthy"])

    def test_partially_stopped_tracks_expected_alive(self):
        watchdog = Watchdog()
        live = SupervisedTask(name="live", factory=_never)
        live.task = _FakeTask(alive=True)
        dead = SupervisedTask(name="dead", factory=_never)
        dead.stopped = True
        watchdog._tasks["live"] = live
        watchdog._tasks["dead"] = dead
        self.assertTrue(watchdog.health()["healthy"])


class EventBusPersistenceTest(unittest.IsolatedAsyncioTestCase):
    async def test_persistence_and_pending_recovery(self):
        with tempfile.TemporaryDirectory(prefix="wave3-events-", dir="/tmp/opencode") as tmp:
            path = str(Path(tmp) / "events.db")
            bus = EventBus(db_path=path)
            try:
                await bus.publish(TaskEvent(EventBus.EVENT_CREATED, "t1"))
                await bus.publish(TaskEvent(EventBus.EVENT_STARTED, "t1"))
                self.assertEqual(bus.get_pending_task_ids(), ["t1"])
                await bus.publish(TaskEvent(EventBus.EVENT_COMPLETED, "t1"))
                self.assertEqual(bus.get_pending_task_ids(), [])
            finally:
                bus.close()

            reopened = EventBus(db_path=path)
            try:
                self.assertEqual(len(reopened.get_history(task_id="t1")), 3)
            finally:
                reopened.close()

    async def test_memory_bus_isolated(self):
        a = EventBus()
        b = EventBus()
        try:
            await a.publish(TaskEvent(EventBus.EVENT_STARTED, "x"))
            self.assertEqual(b.get_history(task_id="x"), [])
        finally:
            a.close()
            b.close()


class NotificationDeliveryTest(unittest.IsolatedAsyncioTestCase):
    def test_compute_availability(self):
        with patch("app.services.notifications.SMTP_CONFIGURED", True):
            status = compute_delivery_availability({"webhook_configured": True, "email_address": "a@b.c"})
            self.assertTrue(status["webhook"])
            self.assertTrue(status["email"])
            self.assertTrue(status["available"])

    async def test_send_user_event_gates_webhook_by_event_kind(self):
        service = NotificationService()
        webhook_calls = []

        async def fake_load(user_id):
            return {
                "webhook_task_done": True,
                "webhook_task_failed": False,
                "webhook_url": "https://example.test/hook",
                "email_address": "",
            }

        async def fake_webhook(url, title, message, event_kind):
            webhook_calls.append((url, title, message, event_kind))
            return True

        service._load_notifications = fake_load
        service._send_webhook = fake_webhook
        service.send = _fake_send

        await service.send_user_event("u1", "Task done", "finished", "task_done")
        self.assertEqual(len(webhook_calls), 1)
        self.assertEqual(webhook_calls[0][3], "task_done")

        webhook_calls.clear()
        await service.send_user_event("u1", "Task failed", "oops", "task_failed")
        self.assertEqual(webhook_calls, [])


async def _fake_send(title, message, **kwargs):
    return False


class StorageSchemaGateTest(unittest.IsolatedAsyncioTestCase):
    async def test_schema_ready_gate(self):
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.addAsyncCleanup(engine.dispose)
        async with engine.connect() as conn:
            self.assertFalse(await _schema_ready(conn))
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with engine.connect() as conn:
            self.assertTrue(await _schema_ready(conn))


class MainCleanupStepTest(unittest.IsolatedAsyncioTestCase):
    async def test_hanging_cleanup_is_timed_out(self):
        async def hang():
            await asyncio.sleep(3600)

        start = time.monotonic()
        await _run_cleanup_step("hang", hang())
        self.assertLess(time.monotonic() - start, SHUTDOWN_STEP_TIMEOUT + 1)

    async def test_raising_cleanup_does_not_propagate(self):
        async def boom():
            raise RuntimeError("teardown exploded")

        await _run_cleanup_step("boom", boom())  # must not raise


if __name__ == "__main__":
    unittest.main()
