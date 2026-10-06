"""Standalone profile checks: no app configuration or shared test database."""

# Standalone unittest execution deliberately avoids the pytest DB fixtures.
# ruff: noqa: PT009, PT027
import sys
import unittest
from datetime import UTC, datetime, timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.profile import PrivacyBoundaryError, ProfileEvent, ProfileLoopService
from app.core.profile.loop import OnlineKMeans, embed_event

# Storage normally imports settings, which can read .env. Supply only the
# settings needed by its isolated in-memory engine before importing storage.
config = ModuleType("app.config")
config.settings = SimpleNamespace(
    app_testing=True,
    test_database_url="sqlite+aiosqlite:///:memory:",
    app_debug=False,
    sqlite_wal=False,
    sqlite_busy_timeout_ms=1000,
    enable_auth=False,
)
# Import the real router and schemas without loading the aggregate API/app.
root = Path(__file__).resolve().parents[2]
schemas_package = ModuleType("app.schemas.api_v1")
schemas_package.__path__ = [str(root / "app/schemas/api_v1")]
with patch.dict(sys.modules, {"app.config": config, "app.schemas.api_v1": schemas_package}):
    from app.core.profile import persistence
    from app.core.profile.persistence import ProfileStore
    from app.core.profile.settings import NOTICE_VERSION
    from app.storage.models_user_profile import UserProfileEvent, UserProfileSnapshot

    spec = spec_from_file_location("isolated_profile_api", root / "app/api/v1/profile.py")
    profile_api = module_from_spec(spec)
    sys.modules[spec.name] = profile_api
    spec.loader.exec_module(profile_api)

NOW = datetime(2026, 10, 2, tzinfo=UTC)


def event(**fields):
    values = {"instruction": "local task", "task_type": "coding", "outcome": "success", "occurred_at": NOW}
    values.update(fields)
    return ProfileEvent(**values)


class ProfileAlgorithmTests(unittest.TestCase):
    def test_half_life_reduces_effective_sample_confidence_by_half(self):
        service = ProfileLoopService(half_life_days=10)
        service.record(event())
        self.assertEqual(service.summary(as_of=NOW).confidence, 0.2)
        self.assertEqual(service.summary(as_of=NOW + timedelta(days=10)).confidence, 0.1)

    def test_success_and_failure_calibrate_equal_frequency_differently(self):
        service = ProfileLoopService()
        service.record(event(task_type="successful"))
        service.record(event(task_type="failed", outcome="failure"))
        summary = service.summary(as_of=NOW)
        self.assertGreater(summary.task_preferences["successful"], summary.task_preferences["failed"])
        self.assertEqual(summary.success_rate, 0.5)

    def test_embedding_is_deterministic_normalized_and_excludes_instruction(self):
        vector = embed_event(event())
        self.assertEqual(len(vector), 12)
        self.assertEqual(vector, embed_event(event(instruction="different private text")))
        self.assertAlmostEqual(sum(value * value for value in vector), 1.0)
        self.assertNotEqual(vector, embed_event(event(task_type="review", tool="browser")))

    def test_online_centroid_uses_weighted_running_mean(self):
        model = OnlineKMeans(k=1, dim=1)
        model.partial_fit((0.0,), weight=1.0)
        model.partial_fit((1.0,), weight=3.0)
        cluster, distance = model.partial_fit((0.75,))
        self.assertEqual(cluster, 0)
        self.assertEqual(distance, 0.0)
        self.assertEqual(model.cluster_weights, (5.0,))

    def test_record_connects_embedding_and_clustering(self):
        service = ProfileLoopService(persona_clusters=1)
        service.record(event())
        service.record(event(tool="terminal"))
        summary = service.summary(as_of=NOW)
        self.assertEqual(summary.persona_cluster, 0)
        self.assertEqual(summary.persona_cluster_confidence, 1.0)

    def test_external_source_is_rejected(self):
        with self.assertRaises(PrivacyBoundaryError):
            ProfileLoopService().record(event(source="purchase_history"))


class ProfileStoreBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as conn:
            for table in (UserProfileEvent.__table__, UserProfileSnapshot.__table__):
                await conn.run_sync(table.create)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.session_patch = patch.object(persistence, "async_session", self.sessions)
        self.session_patch.start()

    async def asyncTearDown(self):
        self.session_patch.stop()
        await self.engine.dispose()

    async def count_events(self):
        async with self.sessions() as db:
            return await db.scalar(select(func.count()).select_from(UserProfileEvent))

    async def test_disabled_record_event_rejects_before_opening_database(self):
        store = ProfileStore(enabled=False)
        with (
            patch.object(persistence, "async_session", side_effect=AssertionError("database opened")),
            self.assertRaisesRegex(ValueError, "profile learning is disabled"),
        ):
            await store.record_event("user", instruction="private text", task_type="coding", outcome="success")
        self.assertEqual(await self.count_events(), 0)

    async def test_disabled_record_run_does_not_persist(self):
        with self.assertRaisesRegex(ValueError, "profile learning is disabled"):
            await ProfileStore(enabled=False).record_run("user", instruction="local run", outcome="failure")
        self.assertEqual(await self.count_events(), 0)

    async def test_disabled_attempt_preserves_existing_events_and_no_hints(self):
        await ProfileStore().update_settings("user", enabled=True, consent_version=NOTICE_VERSION)
        await ProfileStore().record_run("user", instruction="existing run", outcome="success")
        store = ProfileStore(enabled=False)
        with self.assertRaisesRegex(ValueError, "profile learning is disabled"):
            await store.record_run("user", instruction="new run", outcome="failure")
        self.assertEqual(await self.count_events(), 1)
        summary = await store.summary("user")
        self.assertFalse(summary.enabled)
        self.assertEqual(summary.confidence, 0.0)
        context = await store.suggestions("user", "current goal")
        self.assertFalse(context["enabled"])
        self.assertEqual(context["suggestions"], {"task_type": None, "tool": None, "reasoning_level": None})

    async def test_enabled_record_replays_only_own_user_without_raw_instruction(self):
        await ProfileStore().update_settings("user", enabled=True, consent_version=NOTICE_VERSION)
        await ProfileStore().record_run("user", instruction="private raw text", outcome="success")
        self.assertEqual(await self.count_events(), 1)
        async with self.sessions() as db:
            row = (await db.execute(select(UserProfileEvent))).scalar_one()
            self.assertNotIn("instruction", row.__table__.columns)
        summary = await ProfileStore().summary("user")
        self.assertEqual(summary.success_rate, 1.0)
        self.assertEqual((await ProfileStore().summary("other")).task_preferences, {})

    async def test_external_source_does_not_persist(self):
        with self.assertRaises(ValueError):
            await ProfileStore().record_event("user", instruction="text", task_type="coding", outcome="success", source="external")
        self.assertEqual(await self.count_events(), 0)

    async def test_default_requires_explicit_current_notice_consent(self):
        store = ProfileStore()
        settings = await store.get_settings("user")
        self.assertFalse(settings["enabled"])
        self.assertFalse(settings["show_raw_profile"])
        self.assertTrue(settings["consent_required"])
        for version in (None, "old-version"):
            with self.assertRaisesRegex(ValueError, "explicit consent"):
                await store.update_settings("user", enabled=True, consent_version=version)
        with self.assertRaisesRegex(ValueError, "disabled"):
            await store.record_run("user", instruction="before consent", outcome="success")
        self.assertEqual(await self.count_events(), 0)

    async def test_user_settings_isolation_and_fresh_instance_persistence(self):
        settings = await ProfileStore().update_settings("alice", enabled=True, consent_version=NOTICE_VERSION)
        self.assertTrue(settings["enabled"])
        self.assertIsNotNone(settings["consented_at"])
        self.assertTrue((await ProfileStore().get_settings("alice"))["enabled"])
        self.assertFalse((await ProfileStore().get_settings("bob"))["enabled"])
        with self.assertRaisesRegex(ValueError, "disabled"):
            await ProfileStore().record_run("bob", instruction="local", outcome="success")
        await ProfileStore().record_run("alice", instruction="local", outcome="success")
        self.assertEqual(await self.count_events(), 1)

    async def test_shared_background_store_observes_disable_and_resume(self):
        background = ProfileStore()
        await ProfileStore().update_settings("user", enabled=True, consent_version=NOTICE_VERSION)
        await background.record_run("user", instruction="first", outcome="success")
        first = await background.summary("user")
        async with self.sessions() as db:
            snapshot = (await db.execute(select(UserProfileSnapshot))).scalar_one().payload
        await ProfileStore().update_settings("user", enabled=False)
        with self.assertRaisesRegex(ValueError, "disabled"):
            await background.record_run("user", instruction="paused", outcome="failure")
        disabled = await background.summary("user")
        self.assertFalse(disabled.enabled)
        self.assertEqual(disabled.task_preferences, {})
        self.assertEqual(disabled.prompt_hints, ())
        async with self.sessions() as db:
            self.assertEqual((await db.execute(select(UserProfileSnapshot))).scalar_one().payload, snapshot)
        await ProfileStore().update_settings("user", enabled=True)
        resumed = await ProfileStore().summary("user")
        self.assertEqual(resumed.task_preferences, first.task_preferences)
        await background.record_run("user", instruction="resumed", outcome="success")
        self.assertEqual(await self.count_events(), 2)

    async def test_http_settings_consent_user_isolation_and_hidden_profile(self):
        app = FastAPI()
        app.include_router(profile_api.router, prefix="/api/v1/profile")

        def identity(request: Request):
            return request.headers.get("test-user", "alice")

        app.dependency_overrides[profile_api.get_current_user] = identity
        # Exercise real routing/validation; scope policy is a separate fixture.
        for route in profile_api.router.routes:
            for dependency in route.dependant.dependencies:
                if dependency.name == "_auth":
                    app.dependency_overrides[dependency.call] = lambda: {"scopes": ["write"]}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            prefix = "/api/v1/profile"
            initial = await client.get(prefix + "/settings")
            self.assertEqual(initial.status_code, 200)
            self.assertFalse(initial.json()["enabled"])
            self.assertTrue(initial.json()["notice"])
            denied = await client.put(prefix + "/settings", json={"enabled": True})
            self.assertEqual(denied.status_code, 400)
            invalid = await client.put(prefix + "/settings", json={"enabled": "true"})
            self.assertEqual(invalid.status_code, 422)
            enabled = await client.put(prefix + "/settings", json={"enabled": True, "consent_version": initial.json()["notice_version"]})
            self.assertEqual(enabled.status_code, 200)
            self.assertTrue(enabled.json()["enabled"])
            other = await client.get(prefix + "/settings", headers={"test-user": "bob"})
            self.assertFalse(other.json()["enabled"])
            fields = {"instruction": "local task", "task_type": "coding", "outcome": "success"}
            self.assertEqual((await client.post(prefix + "/events", json=fields)).status_code, 200)
            self.assertEqual((await client.get(prefix + "/summary")).status_code, 403)
            self.assertEqual((await client.get(prefix + "/suggestions")).status_code, 403)
            shown = await client.put(prefix + "/settings", json={"enabled": True, "show_raw_profile": True})
            self.assertEqual(shown.status_code, 200)
            self.assertEqual((await client.get(prefix + "/summary")).status_code, 200)
            design = await client.get(prefix + "/clear-design")
            self.assertFalse(design.json()["implemented"])
            self.assertEqual((await client.post(prefix + "/clear")).status_code, 404)
            self.assertEqual(await self.count_events(), 1)
            self.assertEqual((await client.put(prefix + "/settings", json={"enabled": False})).status_code, 200)
            self.assertEqual((await client.post(prefix + "/events", json=fields)).status_code, 400)
            paused = await client.get(prefix + "/summary")
            self.assertEqual(paused.json()["task_preferences"], {})
            self.assertEqual((await client.put(prefix + "/settings", json={"enabled": True})).status_code, 200)
            self.assertTrue((await client.get(prefix + "/summary")).json()["task_preferences"])
            self.assertEqual(await self.count_events(), 1)


if __name__ == "__main__":
    unittest.main()
