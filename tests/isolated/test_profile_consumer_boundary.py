"""Deterministic consumer regressions with a private in-memory profile store."""

import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import test_profile_persistence_window as isolated

from app.core import MessageRole


def load_consumer(name, filename):
    path = Path(__file__).resolve().parents[2] / "app/core/engine" / filename
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dual_loop = load_consumer("isolated_profile_dual_loop", "dual_loop.py")
hooks = load_consumer("isolated_profile_dual_hooks", "dual_loop_hooks.py")
MARKER = "<!-- PROFILE_CONTEXT -->"


class ProfileConsumerBoundaryTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = isolated.ProfilePersistenceWindowTests.asyncSetUp
    enable = isolated.ProfilePersistenceWindowTests.enable

    async def ready(self):
        await self.enable()
        await self.store.record_run(
            "alice",
            instruction="local task",
            task_type="coding",
            outcome="success",
            occurred_at=isolated.NOW,
        )
        coordinator = dual_loop.DualLoopCoordinator()
        coordinator._profile_store = self.store
        coordinator._profile_store_loaded = True
        return coordinator

    def session(self):
        kept = [
            {"role": MessageRole.SYSTEM, "content": "original system"},
            {"role": MessageRole.USER, "content": MARKER + " user quoted marker"},
            {"role": MessageRole.ASSISTANT, "content": "original reply"},
            {"role": MessageRole.TOOL, "content": "original tool result"},
            {"role": MessageRole.USER, "content": "current goal"},
        ]
        session = SimpleNamespace(
            user_id="alice",
            messages=[
                {"role": MessageRole.SYSTEM, "content": MARKER + "\nold profile one"},
                *kept[:2],
                {"role": "system", "content": MARKER + "\nold profile two"},
                *kept[2:],
            ],
        )
        return session, kept

    async def test_disable_between_reads_returns_no_context(self):
        coordinator = await self.ready()
        original = self.store.suggestions

        async def pause(user, instruction):
            await self.store.update_settings(user, enabled=False)
            return await original(user, instruction)

        with patch.object(self.store, "suggestions", pause):
            self.assertEqual(await coordinator.profile_context("alice", "current goal"), "")

    async def test_consent_expires_between_reads_returns_no_context(self):
        coordinator = await self.ready()
        original = self.store.suggestions

        async def expire(user, instruction):
            async with self.sessions() as db:
                row = await db.get(isolated.ProfileLearningSettings, user)
                row.consent_version = "expired-notice"
                await db.commit()
            return await original(user, instruction)

        with patch.object(self.store, "suggestions", expire):
            self.assertEqual(await coordinator.profile_context("alice", "current goal"), "")

    async def test_disabled_or_expired_consent_clears_all_old_profile_messages(self):
        coordinator = await self.ready()
        for mode in ("disabled", "expired"):
            with self.subTest(mode=mode):
                await self.enable()
                if mode == "disabled":
                    await self.store.update_settings("alice", enabled=False)
                else:
                    async with self.sessions() as db:
                        row = await db.get(isolated.ProfileLearningSettings, "alice")
                        row.consented_at = None
                        await db.commit()
                session, kept = self.session()
                messages = session.messages
                await hooks.inject_profile_context(
                    SimpleNamespace(_dual_loop=coordinator), session, "current goal"
                )
                self.assertIs(session.messages, messages)
                self.assertEqual(session.messages, kept)
                for actual, original in zip(session.messages, kept, strict=True):
                    self.assertIs(actual, original)

    async def test_revocation_between_reads_clears_session_profiles(self):
        coordinator = await self.ready()
        original = self.store.suggestions
        for mode in ("disabled", "expired"):
            with self.subTest(mode=mode):
                await self.enable()

                async def revoke(user, instruction, mode=mode):
                    if mode == "disabled":
                        await self.store.update_settings(user, enabled=False)
                    else:
                        async with self.sessions() as db:
                            row = await db.get(isolated.ProfileLearningSettings, user)
                            row.consent_version = "expired-notice"
                            await db.commit()
                    return await original(user, instruction)

                session, kept = self.session()
                with patch.object(self.store, "suggestions", revoke):
                    await hooks.inject_profile_context(
                        SimpleNamespace(_dual_loop=coordinator), session, "current goal"
                    )
                self.assertEqual(session.messages, kept)

    async def test_enabled_refresh_replaces_all_old_profiles_with_one(self):
        coordinator = await self.ready()
        session, kept = self.session()
        await hooks.inject_profile_context(
            SimpleNamespace(_dual_loop=coordinator), session, "current goal"
        )
        profiles = [
            msg
            for msg in session.messages
            if msg["role"] == "system" and msg["content"].startswith(MARKER)
        ]
        self.assertEqual(len(profiles), 1)
        self.assertIn("task_preferences: coding", profiles[0]["content"])
        self.assertEqual([msg for msg in session.messages if msg is not profiles[0]], kept)
        self.assertIs(session.messages[-1], kept[-1])

    async def test_store_exceptions_clear_old_profiles(self):
        coordinator = await self.ready()
        for method in ("summary", "suggestions"):
            with self.subTest(method=method):
                session, kept = self.session()
                with patch.object(
                    self.store, method, AsyncMock(side_effect=RuntimeError("isolated read failure"))
                ):
                    await hooks.inject_profile_context(
                        SimpleNamespace(_dual_loop=coordinator), session, "current goal"
                    )
                self.assertEqual(session.messages, kept)

    async def test_missing_or_raising_coordinator_clears_old_profiles(self):
        for coordinator in (
            None,
            SimpleNamespace(profile_context=AsyncMock(side_effect=RuntimeError("unavailable"))),
        ):
            with self.subTest(coordinator=coordinator):
                session, kept = self.session()
                with patch.object(hooks, "dual_loop_coordinator", return_value=coordinator):
                    await hooks.inject_profile_context(SimpleNamespace(), session, "current goal")
                self.assertEqual(session.messages, kept)

    async def test_missing_enabled_signal_returns_no_context(self):
        coordinator = await self.ready()
        with patch.object(self.store, "suggestions", AsyncMock(return_value={"suggestions": {}})):
            self.assertEqual(await coordinator.profile_context("alice", "current goal"), "")


if __name__ == "__main__":
    unittest.main()
