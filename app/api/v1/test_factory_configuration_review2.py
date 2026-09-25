"""Factory configuration regressions; in-memory DB and scripted task manager only."""

import asyncio
import json
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import skills_router as factory
from app.core.api_key_crypto import encrypt_api_key
from app.storage.database import Agent, ApiKey


class FactoryConfigurationReview2(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Agent.__table__.create)
            await connection.run_sync(ApiKey.__table__.create)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.session_patch = patch.object(factory, "async_session", self.sessions)
        self.session_patch.start()
        self.addCleanup(self.session_patch.stop)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def add_agent(self, id="agent", owner="owner", provider="anthropic",
                        model="user-chosen-model", key="", age=0, active=True, base_url=None):
        async with self.sessions() as db:
            db.add(Agent(
                id=id, user_id=owner, name=id, provider=provider, model_id=model,
                api_key_encrypted=encrypt_api_key(key), base_url=base_url,
                is_active=active, created_at=datetime(2026, 1, 1) + timedelta(days=age),
                system_prompt="User prompt", tool_ids=["calculator"],
            ))
            await db.commit()

    async def add_key(self, id="key", owner="owner", provider="anthropic",
                      key="user-test-key", age=0, active=True, base_url=None):
        async with self.sessions() as db:
            db.add(ApiKey(
                id=id, user_id=owner, provider=provider, name=id,
                api_key_encrypted=encrypt_api_key(key), is_active=active, base_url=base_url,
                created_at=datetime(2026, 1, 1) + timedelta(days=age),
            ))
            await db.commit()

    async def payload(self, **selection):
        return await factory._factory_agent_payload("owner", {"goal": "test", **selection})

    async def test_new_incomplete_agent_does_not_hide_configured_agent(self):
        await self.add_agent(id="configured", model="custom-model")
        await self.add_key(base_url="https://user.example/v1")
        await self.add_agent(id="incomplete", provider="openai", age=1)
        result = await self.payload()
        self.assertEqual(result["agent_id"], "configured")
        self.assertEqual(result["provider"], "anthropic")
        self.assertEqual(result["model"], "custom-model")
        self.assertEqual(result["api_key"], "user-test-key")
        self.assertEqual(result["base_url"], "https://user.example/v1")
        self.assertEqual(result["tools"], ["calculator"])
        self.assertIn("User prompt", result["system_prompt"])

    async def test_explicit_agent_retains_own_model_key_and_endpoint(self):
        await self.add_agent(id="chosen", key="inline-test-key", base_url="https://agent.example/v1")
        await self.add_agent(id="newer", key="different-test-key", age=1)
        await self.add_key(base_url="https://other.example/v1")
        result = await self.payload(agent_id="chosen")
        self.assertEqual(result["agent_id"], "chosen")
        self.assertEqual(result["model"], "user-chosen-model")
        self.assertEqual(result["api_key"], "inline-test-key")
        self.assertEqual(result["base_url"], "https://agent.example/v1")

    async def test_explicit_incomplete_agent_keeps_409(self):
        await self.add_agent(id="chosen", provider="openai")
        await self.add_agent(id="other", key="configured-test-key")
        with self.assertRaises(HTTPException) as error:
            await self.payload(agent_id="chosen")
        self.assertEqual(error.exception.status_code, 409)

    async def test_key_only_uses_explicit_non_openai_provider_and_model(self):
        await self.add_key(provider="stepfun", base_url="https://user.example/v1")
        result = await self.payload(provider="stepfun", model="user-step-model")
        self.assertEqual(result["provider"], "stepfun")
        self.assertEqual(result["model"], "user-step-model")
        self.assertEqual(result["api_key"], "user-test-key")
        self.assertIsNone(result["agent_id"])

    async def test_key_only_requires_user_model_instead_of_default(self):
        await self.add_key(provider="stepfun")
        with self.assertRaises(HTTPException) as error:
            await self.payload()
        self.assertEqual(error.exception.status_code, 409)

    async def test_foreign_or_inactive_keys_are_never_selected(self):
        await self.add_agent()
        await self.add_key(id="foreign", owner="other-owner")
        await self.add_key(id="inactive", active=False)
        await self.add_key(id="mismatch", provider="openai")
        with self.assertRaises(HTTPException) as error:
            await self.payload()
        self.assertEqual(error.exception.status_code, 409)

    async def test_foreign_or_inactive_agents_are_never_selected(self):
        await self.add_agent(id="foreign", owner="other-owner", key="foreign-key")
        await self.add_agent(id="inactive", active=False, key="inactive-key")
        for selection, status in [({}, 409), ({"agent_id": "foreign"}, 404), ({"agent_id": "inactive"}, 404)]:
            with self.subTest(selection=selection), self.assertRaises(HTTPException) as error:
                await self.payload(**selection)
            self.assertEqual(error.exception.status_code, status)

    async def test_empty_and_unreadable_keys_do_not_hide_valid_key(self):
        await self.add_agent()
        await self.add_key(id="valid")
        await self.add_key(id="empty", key="   ", age=1)
        await self.add_key(id="corrupt", key="enc:v1:invalid-test-data", age=2)
        self.assertEqual((await self.payload())["api_key"], "user-test-key")

    async def test_unreadable_key_retains_actionable_409(self):
        await self.add_agent(key="enc:v1:invalid-test-data")
        with self.assertRaises(HTTPException) as error:
            await self.payload()
        self.assertEqual(error.exception.status_code, 409)
        self.assertIn("cannot be decrypted", error.exception.detail)

    async def test_missing_model_is_not_filled(self):
        await self.add_agent(model=" ", key="user-test-key")
        with self.assertRaises(HTTPException) as error:
            await self.payload()
        self.assertEqual(error.exception.status_code, 409)

    async def test_request_cannot_supply_owner_or_credentials(self):
        await self.add_agent(owner="other-owner", key="foreign-test-key")
        with self.assertRaises(HTTPException) as error:
            await self.payload(user_id="other-owner", owner_id="other-owner",
                               provider="anthropic", model="chosen", api_key="request-test-key")
        self.assertEqual(error.exception.status_code, 409)

    async def test_ambiguous_or_partial_selection_is_rejected(self):
        for selection in [dict(provider="openai"), dict(model="chosen"),
                          dict(agent_id="agent", provider="openai", model="chosen")]:
            with self.subTest(selection=selection), self.assertRaises(HTTPException) as error:
                await self.payload(**selection)
            self.assertEqual(error.exception.status_code, 422)

    async def test_ollama_config_is_keyless_without_claiming_health(self):
        await self.add_agent(provider="ollama", model="installed-model", base_url="http://localhost:11434")
        result = await self.payload()
        self.assertEqual(result["api_key"], "")
        self.assertEqual(result["model"], "installed-model")
        self.assertNotIn("healthy", result)
        self.assertNotIn("available", result)

    async def test_keyless_ollama_preserves_saved_endpoint(self):
        await self.add_key(provider="ollama", key="", base_url="http://user-ollama:11434")
        result = await self.payload(provider="ollama", model="user-local-model")
        self.assertEqual(result["base_url"], "http://user-ollama:11434")
        self.assertEqual(result["api_key"], "")

    async def stream_result(self, status, disconnected=False, provider="anthropic", key="user-test-key"):
        await self.add_agent(key=key, provider=provider)
        queue = asyncio.Queue()
        queue.put_nowait({"type": "progress", "data": {"message": "scripted"}})
        manager = SimpleNamespace(
            submit=AsyncMock(return_value="run"), subscribe=Mock(return_value=queue),
            get_status=AsyncMock(return_value=status), cancel=AsyncMock(return_value=True),
            unsubscribe=Mock(),
        )
        request = SimpleNamespace(is_disconnected=AsyncMock(return_value=disconnected))
        with patch.object(factory, "task_manager", manager), \
             patch.object(factory, "_payload", AsyncMock(return_value={"goal": "test"})), \
             patch.object(factory, "current_user_id", return_value="owner"):
            response = await factory.run_autonomous_skill(request)
            chunks = [chunk async for chunk in response.body_iterator]
        manager.submit.assert_awaited_once()
        self.assertEqual(manager.submit.call_args.kwargs, {"owner_id": "owner"})
        if not disconnected:
            manager.get_status.assert_awaited_once_with("run", owner_id="owner")
        manager.unsubscribe.assert_called_once_with("run", queue)
        text = "".join(chunks)
        self.assertNotIn("user-test-key", text)
        events = [json.loads(block.split("data: ")[1]) for block in text.split("\n\n")
                  if block.startswith("event:")]
        return events, manager

    async def test_completed_status_produces_explicit_terminal_event(self):
        events, _ = await self.stream_result({"status": "completed"})
        self.assertEqual(events[0]["type"], "factory_config")
        self.assertEqual(events[0]["data"]["model"], "user-chosen-model")
        self.assertEqual(events[-1]["type"], "factory_completed")

    async def test_failure_keeps_actual_backend_error(self):
        events, _ = await self.stream_result({"status": "failed", "error": "model endpoint unavailable"})
        self.assertEqual(events[-1]["type"], "factory_failed")
        self.assertEqual(events[-1]["data"]["error"], "model endpoint unavailable")

    async def test_keyless_ollama_endpoint_failure_is_not_reported_as_success(self):
        events, _ = await self.stream_result(
            {"status": "failed", "error": "Ollama connection refused"},
            provider="ollama", key="",
        )
        self.assertEqual(events[-1]["data"]["error"], "Ollama connection refused")
        self.assertNotIn("factory_completed", [event["type"] for event in events])

    async def test_cancelled_status_is_distinct_from_success(self):
        events, _ = await self.stream_result({"status": "cancelled"})
        self.assertEqual(events[-1]["data"]["status"], "cancelled")
        self.assertNotIn("factory_completed", [event["type"] for event in events])

    async def test_missing_task_status_is_failure(self):
        events, _ = await self.stream_result(None)
        self.assertEqual(events[-1]["type"], "factory_failed")

    async def test_disconnect_cancels_submitted_task(self):
        events, manager = await self.stream_result(None, disconnected=True)
        manager.cancel.assert_awaited_once_with("run")
        self.assertNotIn("factory_completed", [event["type"] for event in events])

    async def test_missing_configuration_never_submits(self):
        with patch.object(factory, "task_manager") as manager, \
             patch.object(factory, "_payload", AsyncMock(return_value={"goal": "test"})), \
             patch.object(factory, "current_user_id", return_value="owner"):
            with self.assertRaises(HTTPException) as error:
                await factory.run_autonomous_skill(Mock())
            self.assertEqual(error.exception.status_code, 409)
            manager.submit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
