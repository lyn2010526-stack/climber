"""Standalone persistence regressions using only a private in-memory database."""

# ruff: noqa: PT009, PT027
import json
import sys
import unittest
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.core.profile import ProfileLoopService, loop


class Base(DeclarativeBase):
    pass


# Load the real models/repository without importing storage initialization,
# application configuration, API modules or shared pytest database fixtures.
storage = ModuleType("app.storage")
storage.__path__ = [str(Path(__file__).resolve().parents[2] / "app/storage")]
storage.Base = Base
storage.async_session = None
with patch.dict(sys.modules, {"app.storage": storage}):
    from app.core.profile import persistence
    from app.core.profile.persistence import ProfileStore
    from app.core.profile.settings import NOTICE_VERSION, ProfileLearningSettings
    from app.storage.models_user_profile import UserProfileEvent, UserProfileSnapshot

NOW = datetime(2026, 10, 2, tzinfo=UTC)


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW if tz else NOW.replace(tzinfo=None)


def create_profile_tables(db):
    from app.core.profile import settings as profile_settings

    metadata = UserProfileEvent.metadata
    wanted = {
        UserProfileEvent.__tablename__,
        UserProfileSnapshot.__tablename__,
        profile_settings.ProfileLearningSettings.__tablename__,
    }
    tables = [table for table in metadata.sorted_tables if table.name in wanted]
    metadata.create_all(db, tables=tables)


class ProfilePersistenceWindowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.addAsyncCleanup(self.engine.dispose)
        async with self.engine.begin() as conn:
            await conn.run_sync(create_profile_tables)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.enterContext(patch.object(persistence, "async_session", self.sessions))
        self.enterContext(patch.object(loop, "datetime", FrozenDatetime))
        self.enterContext(patch.object(persistence, "REPLAY_EVENT_LIMIT", 2))
        self.store = ProfileStore()

    async def enable(self, user="alice"):
        await self.store.update_settings(user, enabled=True, consent_version=NOTICE_VERSION)

    async def seed(self, user, events):
        async with self.sessions() as db:
            for event_id, days, task, outcome in events:
                db.add(UserProfileEvent(
                    id=event_id, user_id=user, occurred_at=NOW + timedelta(days=days),
                    task_type=task, outcome=outcome, source="agent_internal",
                ))
            await db.commit()

    async def snapshot(self, user="alice"):
        async with self.sessions() as db:
            row = await db.get(UserProfileSnapshot, user)
            return dict(row.payload) if row else None

    async def test_recent_window_is_chronological_and_user_isolated(self):
        await self.enable()
        await self.enable("bob")
        await self.seed("alice", [
            ("a-new", 0, "new", "success"),
            ("a-old", -3, "old", "failure"),
            ("a-middle", -1, "middle", "success"),
        ])
        await self.seed("bob", [("b", 1, "other-user", "failure")])
        recorded = []
        original = ProfileLoopService.record

        def capture(service, event):
            recorded.append(event.task_type)
            return original(service, event)

        with patch.object(ProfileLoopService, "record", capture):
            summary = await self.store.summary("alice")
        self.assertEqual(recorded, ["middle", "new"])
        self.assertEqual(set(summary.task_preferences), {"middle", "new"})
        self.assertEqual(summary.success_rate, 1.0)
        context = await self.store.suggestions("alice", "current instruction")
        self.assertEqual(context["task_preferences"], summary.task_preferences)
        self.assertEqual(context["current_instruction"], "current instruction")

    async def test_equal_timestamps_use_id_for_window_and_replay_order(self):
        await self.enable()
        await self.seed("alice", [(key, 0, key, "success") for key in ("c", "a", "b")])
        service = await self.store._load_service("alice")
        self.assertEqual([event.task_type for event in service._events], ["b", "c"])
        self.assertEqual(service.summary(), (await self.store._load_service("alice")).summary())

    async def test_limit_one_selects_latest_event(self):
        await self.enable()
        await self.seed("alice", [("a", -1, "old", "failure"), ("b", 0, "new", "success")])
        with patch.object(persistence, "REPLAY_EVENT_LIMIT", 1):
            summary = await self.store.summary("alice")
        self.assertEqual(set(summary.task_preferences), {"new"})
        self.assertEqual(summary.success_rate, 1.0)

    async def test_empty_and_under_limit_windows(self):
        await self.enable()
        empty = await self.store.summary("alice")
        self.assertTrue(empty.enabled)
        self.assertEqual(empty.task_preferences, {})
        await self.seed("alice", [("a", 0, "single", "success")])
        summary = await self.store.summary("alice")
        self.assertEqual(summary, (await self.store._load_service("alice")).summary())
        self.assertEqual(summary.confidence, 0.2)

    async def test_repeated_reads_after_new_event_are_idempotent(self):
        await self.enable()
        await self.store.record_run("alice", instruction="first", task_type="old", outcome="success", occurred_at=NOW)
        await self.store.summary("alice")
        await self.store.record_run("alice", instruction="second", task_type="new", outcome="failure", occurred_at=NOW)
        expected = (await self.store._load_service("alice")).summary()
        first = await self.store.summary("alice")
        self.assertEqual(first, expected)
        for _ in range(3):
            self.assertEqual(await ProfileStore().summary("alice"), first)
            self.assertEqual(await self.snapshot(), json.loads(json.dumps(asdict(first))))
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(UserProfileSnapshot)), 1)

    async def test_evicted_events_do_not_linger_in_snapshot(self):
        await self.enable()
        await self.seed("alice", [("a", -2, "old", "failure")])
        await self.store.summary("alice")
        await self.seed("alice", [("b", -1, "middle", "success"), ("c", 0, "new", "success")])
        summary = await self.store.summary("alice")
        self.assertEqual(set(summary.task_preferences), {"middle", "new"})
        self.assertEqual(summary.success_rate, 1.0)

    async def test_current_consent_and_timestamp_are_required_for_reads_and_writes(self):
        await self.seed("alice", [("a", 0, "archived", "success")])
        for version in (None, "old-version"):
            with self.assertRaisesRegex(ValueError, "explicit consent"):
                await self.store.update_settings("alice", enabled=True, consent_version=version)
        for version, consented_at in ((None, None), ("old-version", NOW), (NOTICE_VERSION, None)):
            async with self.sessions() as db:
                row = await db.get(ProfileLearningSettings, "alice")
                if row is None:
                    row = ProfileLearningSettings(user_id="alice")
                    db.add(row)
                row.enabled, row.consent_version, row.consented_at = True, version, consented_at
                await db.commit()
            self.assertFalse((await self.store.summary("alice")).enabled)
            self.assertFalse((await self.store.suggestions("alice", "goal"))["enabled"])
            with self.assertRaisesRegex(ValueError, "disabled"):
                await self.store.record_run("alice", instruction="blocked", outcome="success")
            self.assertIsNone(await self.snapshot())
        await self.enable()
        self.assertTrue((await self.store.summary("alice")).enabled)
        self.assertFalse((await self.store.summary("bob")).enabled)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(UserProfileEvent)), 1)

    async def test_disable_preserves_snapshot_and_resume_rebuilds(self):
        await self.enable()
        await self.store.record_run("alice", instruction="first", outcome="success", occurred_at=NOW)
        first = await self.store.summary("alice")
        snapshot = await self.snapshot()
        await self.store.update_settings("alice", enabled=False)
        self.assertFalse((await self.store.summary("alice")).enabled)
        self.assertFalse((await ProfileStore(enabled=False).summary("alice")).enabled)
        self.assertFalse((await self.store.suggestions("alice", "goal"))["enabled"])
        with self.assertRaisesRegex(ValueError, "disabled"):
            await self.store.record_run("alice", instruction="paused", outcome="failure")
        self.assertEqual(await self.snapshot(), snapshot)
        await self.store.update_settings("alice", enabled=True)
        self.assertEqual(await self.store.summary("alice"), first)

    async def test_disable_during_replay_blocks_snapshot_refresh(self):
        await self.enable()
        original = self.store._load_service

        async def pause_after_load(user):
            service = await original(user)
            await self.store.update_settings(user, enabled=False)
            return service

        with patch.object(self.store, "_load_service", pause_after_load):
            self.assertFalse((await self.store.summary("alice")).enabled)
        self.assertIsNone(await self.snapshot())

    async def test_disable_during_replay_blocks_old_suggestions(self):
        await self.enable()
        await self.store.record_run("alice", instruction="first", task_type="coding", outcome="success", occurred_at=NOW)
        original = self.store._load_service

        async def pause_after_load(user):
            service = await original(user)
            await self.store.update_settings(user, enabled=False)
            return service

        with patch.object(self.store, "_load_service", pause_after_load):
            context = await self.store.suggestions("alice", "current goal")
        self.assertFalse(context["enabled"])
        self.assertEqual(context["task_preferences"], {})
        self.assertEqual(context["suggestions"], {"task_type": None, "tool": None, "reasoning_level": None})
        self.assertEqual(context["current_instruction"], "current goal")


if __name__ == "__main__":
    unittest.main()
