"""Multimodal image contract for the chat API and provider message paths.

Covers: request validation, real engine parts construction, storage (message
metadata), OpenAI vision passthrough, provider degradation and adapter
conversions. Follows the fake-adapter style of
``tests/test_chat_model_credentials.py``; no network.
"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import FastAPI
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import chat, router, sessions
from app.core import AgentEvent, AgentEventType, ChatResult
from app.core.agent_engine import AgentEngine
from app.core.api_key_crypto import encrypt_api_key
from app.core.auth import get_current_user
from app.core.engine.run_storage import RunStorage
from app.core.session import AgentSession, SessionConfig
from app.models import ModelCapability
from app.models.anthropic_adapter import AnthropicAdapter
from app.models.google_adapter import GoogleGeminiAdapter
from app.models.ollama_adapter import OllamaAdapter
from app.models.openai_adapter import OpenAIAdapter
from app.models.registry import PROVIDERS, ModelRegistry
from app.models.vision import (
    MAX_CHAT_IMAGES,
    build_user_content,
    content_text,
    degrade_image_parts,
    image_parts,
    is_image_reference,
    split_data_url,
    validate_attachments,
    validate_images,
)
from app.storage import Base
from app.storage.database import (
    Agent,
    ApiKey,
    CheckpointRecord,
    Message,
    Session,
    SessionInput,
    Turn,
    UsageLog,
)

PNG_DATA_URL = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="
JPEG_DATA_URL = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/"
WEB_URL = "https://example.com/cat.png"


class VisionHelperTests(unittest.IsolatedAsyncioTestCase):
    async def test_reference_validation_accepts_data_and_web_urls(self):
        self.assertTrue(is_image_reference(PNG_DATA_URL))
        self.assertTrue(is_image_reference(WEB_URL))
        self.assertFalse(is_image_reference("ftp://example.com/x.png"))
        self.assertFalse(is_image_reference("data:text/html;base64,PGI+"))
        self.assertFalse(is_image_reference("data:image/png;base64,not-b64!!"))

    async def test_validate_images_rejects_overflow_and_malformed(self):
        self.assertEqual(validate_images(None), [])
        self.assertEqual(validate_images([]), [])
        with self.assertRaises(ValueError):
            validate_images([PNG_DATA_URL] * (MAX_CHAT_IMAGES + 1))
        with self.assertRaises(ValueError):
            validate_images([PNG_DATA_URL, "not-a-url"])

    async def test_build_user_content_parts(self):
        self.assertEqual(build_user_content("hi", None), "hi")
        self.assertEqual(build_user_content("hi", []), "hi")
        parts = build_user_content("hi", [PNG_DATA_URL, WEB_URL])
        self.assertEqual(parts[0], {"type": "text", "text": "hi"})
        self.assertEqual(parts[1], {"type": "image_url", "image_url": {"url": PNG_DATA_URL}})
        self.assertEqual(parts[2], {"type": "image_url", "image_url": {"url": WEB_URL}})

    async def test_content_helpers(self):
        parts = build_user_content("hi", [PNG_DATA_URL])
        self.assertEqual(content_text(parts), "hi")
        self.assertEqual(
            image_parts(parts), [{"type": "image_url", "image_url": {"url": PNG_DATA_URL}}]
        )
        self.assertEqual(image_parts("plain"), [])

    async def test_split_data_url(self):
        self.assertEqual(split_data_url(PNG_DATA_URL), ("image/png", "iVBORw0KGgoAAAANSUhEUg=="))
        self.assertIsNone(split_data_url(WEB_URL))
        self.assertIsNone(split_data_url("data:image/png;base64,%%%"))

    async def test_validate_file_attachment_requires_matching_size_and_type(self):
        import base64

        data = base64.b64encode(b"hello").decode()
        self.assertEqual(
            validate_attachments(
                [
                    {
                        "kind": "file",
                        "data": f"data:text/plain;base64,{data}",
                        "name": "notes.txt",
                        "mime_type": "text/plain",
                        "size": 5,
                    }
                ]
            )[0].name,
            "notes.txt",
        )
        with self.assertRaises(ValueError):
            validate_attachments(
                [
                    {
                        "kind": "file",
                        "data": f"data:text/plain;base64,{data}",
                        "name": "notes.txt",
                        "mime_type": "text/plain",
                        "size": 4,
                    }
                ]
            )

    async def test_degrade_flattens_parts_and_keeps_plain_messages(self):
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": build_user_content("look", [PNG_DATA_URL, WEB_URL])},
            {"role": "assistant", "content": "ok"},
        ]
        degraded = degrade_image_parts(messages, provider="ollama", model_id="llama3")
        self.assertEqual(degraded[1]["content"], "look")
        self.assertEqual(degraded[0]["content"], "sys")
        self.assertEqual(degraded[2]["content"], "ok")
        self.assertEqual(messages[1]["content"][1]["type"], "image_url")

    async def test_degrade_without_images_returns_same_list(self):
        messages = [{"role": "user", "content": "hi"}]
        self.assertIs(degrade_image_parts(messages, provider="openai", model_id="gpt-4o"), messages)


class FakeAdapter:
    def __init__(self, **kwargs):
        self.config = kwargs


class RecordingEngine(AgentEngine):
    """Records the run arguments; only run/constructor are faked."""

    def __init__(self):
        self._sessions = {}
        self._session_locks = {}
        self.model_registry = ModelRegistry()
        self.runs = []

    def _init_reasoning(self):
        pass

    async def run(self, _session, _message, images=None):
        self.runs.append((_message, images))
        yield AgentEvent(type=AgentEventType.TEXT, data={"content": "image reply"})


class ChatImageApiTests(unittest.IsolatedAsyncioTestCase):
    """Endpoint contract: validation and the chat -> engine argument passing."""

    async def asyncSetUp(self):
        self.database = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.addAsyncCleanup(self.database.dispose)
        tables = [Agent.__table__, ApiKey.__table__, Session.__table__, Message.__table__]
        async with self.database.begin() as connection:
            await connection.run_sync(lambda conn: Agent.metadata.create_all(conn, tables=tables))
        self.db = async_sessionmaker(self.database, expire_on_commit=False)
        async with self.db() as db:
            db.add_all(
                [
                    Agent(
                        id="agent-a",
                        user_id="owner-a",
                        name="A",
                        provider="openai",
                        model_id="agent-model",
                        api_key_encrypted=encrypt_api_key("agent-secret"),
                        base_url="https://agent.example/v1",
                    ),
                    ApiKey(
                        id="key-a",
                        user_id="owner-a",
                        provider="openai",
                        name="A",
                        api_key_encrypted=encrypt_api_key("selected-secret-a"),
                        base_url="https://selected.example/v1",
                        is_active=True,
                    ),
                ]
            )
            await db.commit()
        self.owner = "owner-a"
        self.engine = RecordingEngine()
        for target in (chat, sessions):
            patcher = patch.object(target, "async_session", self.db)
            patcher.start()
            self.addCleanup(patcher.stop)
        for patcher in [
            patch.object(chat, "get_engine", return_value=self.engine),
            patch.object(
                chat.RecoveryManager, "restore_session", new_callable=AsyncMock, return_value=False
            ),
            patch.dict(PROVIDERS, {"openai": FakeAdapter}),
            patch.object(
                ModelRegistry,
                "_resolve_spec",
                side_effect=AssertionError("No environment fallback"),
            ),
        ]:
            patcher.start()
            self.addCleanup(patcher.stop)
        chat._chat_inflight.clear()
        self.addCleanup(chat._chat_inflight.clear)
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_current_user] = lambda: self.owner
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )
        self.addAsyncCleanup(self.client.aclose)

    async def create_session(self):
        response = await self.client.post(
            "/api/v1/sessions",
            json={
                "agent_id": "agent-a",
                "model_settings": {
                    "credential_id": "key-a",
                    "provider": "openai",
                    "model_id": "chosen",
                },
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["id"]

    async def send(self, session_id, **payload):
        body = {"message": "what is in this picture?", **payload}
        return await self.client.post(f"/api/v1/sessions/{session_id}/chat", json=body)

    async def test_text_only_request_keeps_legacy_contract(self):
        sid = await self.create_session()
        response = await self.send(sid)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("image reply", response.text)
        message, images = self.engine.runs[-1]
        self.assertEqual(message, "what is in this picture?")
        self.assertIsNone(images)

    async def test_images_are_forwarded_to_the_engine(self):
        sid = await self.create_session()
        response = await self.send(sid, images=[PNG_DATA_URL, WEB_URL])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("image reply", response.text)
        message, images = self.engine.runs[-1]
        self.assertEqual(message, "what is in this picture?")
        self.assertEqual(images, [PNG_DATA_URL, WEB_URL])

    async def test_invalid_image_reference_is_rejected_with_422(self):
        sid = await self.create_session()
        response = await self.send(sid, images=["data:text/html;base64,PGI+"])
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.engine.runs, [])

    async def test_too_many_images_is_rejected_with_422(self):
        sid = await self.create_session()
        response = await self.send(sid, images=[PNG_DATA_URL] * (MAX_CHAT_IMAGES + 1))
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.engine.runs, [])


class ScriptedModel:
    """An explicit fake model; no network or real LLM is exercised."""

    def __init__(self, response, streaming=False):
        self.response = response
        self.capabilities = SimpleNamespace(streaming=streaming, max_tokens=100000)
        self.seen = []

    async def chat(self, messages, **_kwargs):
        self.seen.append(list(messages))
        return self.response

    async def stream_chat(self, messages, **_kwargs):
        self.seen.append(list(messages))
        yield self.response


class EngineImageStorageTests(unittest.IsolatedAsyncioTestCase):
    """Real engine path: parts construction, adapter passthrough and storage."""

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="chat-images-")
        self.addAsyncCleanup(self.tmp.cleanup)
        self.db_engine = create_async_engine(
            "sqlite+aiosqlite:///" + str(Path(self.tmp.name) / "images.db")
        )

        @event.listens_for(self.db_engine.sync_engine, "connect")
        def foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

        self.factory = async_sessionmaker(self.db_engine, expire_on_commit=False)
        tables = [
            model.__table__
            for model in (Agent, Session, SessionInput, Turn, Message, UsageLog, CheckpointRecord)
        ]
        async with self.db_engine.begin() as connection:
            await connection.run_sync(lambda conn: Base.metadata.create_all(conn, tables=tables))
        for patcher in [
            patch("app.storage.async_session", self.factory),
            patch.object(AgentEngine, "_init_sandbox", lambda eng: setattr(eng, "sandbox", None)),
            patch.object(AgentEngine, "_init_reasoning"),
            patch.object(AgentEngine, "_init_permissions"),
            patch.object(AgentEngine, "_set_agent_mode"),
            patch.object(AgentEngine, "_send_start_notification"),
            patch.object(AgentEngine, "_send_completion_notification"),
            patch.object(AgentEngine, "_send_failure_notification"),
            patch.object(AgentEngine, "_inject_memory_context", new_callable=AsyncMock),
            patch.object(AgentEngine, "_inject_core_memory", new_callable=AsyncMock),
            patch.object(AgentEngine, "_store_episodic_memory", new_callable=AsyncMock),
            patch.object(AgentEngine, "_trigger_memory_reflection"),
            patch("app.core.agent_engine.build_tools", return_value=[]),
        ]:
            patcher.start()
            self.addCleanup(patcher.stop)

    def engine(self, model):
        engine = AgentEngine(
            model_registry=SimpleNamespace(get_or_create=lambda **_kwargs: model),
            tool_registry=Mock(),
            run_store=RunStorage(self.factory),
        )
        engine.permission_overlay = None
        engine.agent_mode = None
        return engine

    def session(self, sid="session"):
        return AgentSession(
            SessionConfig(
                session_id=sid,
                user_id="audit-user",
                agent_id="",
                provider="scripted-test",
                model_id="fake-model",
            )
        )

    async def user_rows(self):
        async with self.factory() as db:
            return list(
                (
                    await db.execute(
                        select(Message).where(Message.role == "user"),
                    )
                ).scalars()
            )

    async def test_image_message_becomes_parts_and_persists_metadata(self):
        model = ScriptedModel(ChatResult(content="ok", tokens_used=1))
        images = [PNG_DATA_URL, WEB_URL]
        session = self.session()
        async for _event in self.engine(model).run(session, "look", images=images):
            pass

        user_message = next(msg for msg in reversed(session.messages) if msg["role"] == "user")
        self.assertEqual(user_message["role"], "user")
        self.assertEqual(user_message["content"][0], {"type": "text", "text": "look"})
        self.assertEqual(
            user_message["content"][1], {"type": "image_url", "image_url": {"url": PNG_DATA_URL}}
        )
        self.assertEqual(
            user_message["content"][2], {"type": "image_url", "image_url": {"url": WEB_URL}}
        )
        self.assertEqual(model.seen[0][-1]["content"][1]["type"], "image_url")

        rows = await self.user_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].content, "look")
        self.assertEqual(rows[0].metadata_.get("images"), images)

    async def test_plain_message_stores_no_images(self):
        model = ScriptedModel(ChatResult(content="ok", tokens_used=1))
        session = self.session()
        async for _event in self.engine(model).run(session, "hello"):
            pass

        user_message = next(msg for msg in reversed(session.messages) if msg["role"] == "user")
        self.assertEqual(user_message["content"], "hello")
        rows = await self.user_rows()
        self.assertEqual(rows[0].content, "hello")
        self.assertEqual(rows[0].metadata_.get("images"), None)


class OpenAIVisionPassthroughTests(unittest.TestCase):
    def adapter(self, vision=None):
        capabilities = None
        if vision is not None:
            capabilities = ModelCapability(chat=True, streaming=True, tools=True, vision=vision)
        return OpenAIAdapter("gpt-4o", "test-key", capabilities=capabilities)

    def test_vision_payload_keeps_content_parts(self):
        adapter = self.adapter(vision=True)
        messages = [{"role": "user", "content": build_user_content("hi", [PNG_DATA_URL])}]
        payload = adapter._build_payload(messages)
        content = payload["messages"][0]["content"]
        self.assertEqual(content[1], {"type": "image_url", "image_url": {"url": PNG_DATA_URL}})

    def test_non_vision_payload_degrades_to_text(self):
        with patch("app.models.vision.logger") as degrade_logger:
            adapter = self.adapter(vision=False)
            messages = [
                {"role": "user", "content": build_user_content("hi", [PNG_DATA_URL, WEB_URL])}
            ]
            payload = adapter._build_payload(messages)
            self.assertEqual(payload["messages"][0]["content"], "hi")
            self.assertEqual(
                payload["messages"][0]["content"], content_text(messages[0]["content"])
            )
            degrade_logger.warning.assert_called_once()

    def test_default_openai_capability_allows_vision(self):
        self.assertTrue(self.adapter().capabilities.vision)

    def test_stepfun_default_degrades(self):
        from app.models.stepfun_adapter import StepFunAdapter

        adapter = StepFunAdapter("step-3.5-flash", "test-key")
        self.assertFalse(adapter.capabilities.vision)
        messages = [{"role": "user", "content": build_user_content("hi", [PNG_DATA_URL])}]
        payload = adapter._build_payload(messages)
        self.assertEqual(payload["messages"][0]["content"], "hi")


class AnthropicVisionConversionTests(unittest.TestCase):
    def convert(self, content):
        return AnthropicAdapter("claude-3-5-sonnet-20240620", "test-key")._convert_content(content)

    def test_text_only_content_passes_through(self):
        self.assertEqual(self.convert("hello"), "hello")

    def test_data_url_becomes_base64_source(self):
        blocks = self.convert(build_user_content("hi", [PNG_DATA_URL]))
        self.assertEqual(blocks[0], {"type": "text", "text": "hi"})
        self.assertEqual(
            blocks[1],
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": "iVBORw0KGgoAAAANSUhEUg==",
                },
            },
        )

    def test_web_url_becomes_url_source(self):
        blocks = self.convert(build_user_content("hi", [WEB_URL]))
        self.assertEqual(blocks[1], {"type": "image", "source": {"type": "url", "url": WEB_URL}})


class GeminiVisionConversionTests(unittest.TestCase):
    def convert(self, content):
        return GoogleGeminiAdapter._convert_content(content)

    def test_text_only_content_becomes_single_text_part(self):
        self.assertEqual(self.convert("hello"), [{"text": "hello"}])

    def test_data_url_becomes_inline_data(self):
        parts = self.convert(build_user_content("hi", [JPEG_DATA_URL]))
        self.assertEqual(parts[0], {"text": "hi"})
        self.assertEqual(
            parts[1],
            {
                "inline_data": {"mime_type": "image/jpeg", "data": "/9j/4AAQSkZJRgABAQAAAQABAAD/"},
            },
        )

    def test_web_url_becomes_file_data(self):
        parts = self.convert(build_user_content("hi", [WEB_URL]))
        self.assertEqual(parts[1], {"file_data": {"file_uri": WEB_URL}})


class OllamaDegradeTests(unittest.IsolatedAsyncioTestCase):
    async def test_offline_queue_payload_flattens_image_parts(self):
        from app.services.ollama_queue import ollama_offline_queue

        adapter = OllamaAdapter("llama3", "")
        with (
            patch.object(
                adapter, "_is_ollama_reachable", new_callable=AsyncMock, return_value=False
            ),
            patch("app.models.vision.logger") as degrade_logger,
            patch("app.services.ollama_queue.logger"),
        ):
            messages = [{"role": "user", "content": build_user_content("hi", [PNG_DATA_URL])}]
            result = await adapter.chat(messages)
            self.assertEqual(result.finish_reason, "offline")

        queued = ollama_offline_queue._queue[-1].payload
        self.assertEqual(queued["messages"][0]["content"], "hi")
        degrade_logger.warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
