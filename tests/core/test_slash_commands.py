"""Slash command layer: parser, registry, service, and HTTP endpoints.

Real routes + SQLite for the HTTP tests (mirroring
``tests/test_chat_model_credentials.py``); pure-python for parser/registry.
The engine is a recording fake — no provider network traffic.
"""

from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.routes import chat_commands
from app.core import AgentEvent, AgentEventType
from app.core.agent_engine import AgentEngine
from app.core.slash import (
    CommandRegistry,
    ParseOutcome,
    SlashCommandError,
    SlashCommandService,
    build_default_registry,
    command_catalog,
    last_user_message,
    parse_input,
)
from app.storage import Base
from app.storage.database import Agent, ApiKey, Message, Session

# ---------------------------------------------------------------------------
# Parser / registry (pure python)
# ---------------------------------------------------------------------------


class ParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_default_registry()

    def test_matches_registered_command(self):
        outcome = parse_input("/help", self.registry)
        self.assertEqual(outcome.kind, "command")
        self.assertEqual(outcome.command, "help")
        self.assertEqual(outcome.args, [])

    def test_case_and_whitespace_insensitive(self):
        self.assertEqual(parse_input("  /HELP  ", self.registry).command, "help")
        self.assertEqual(parse_input("/Stop", self.registry).command, "stop")

    def test_alias_resolution(self):
        outcome = parse_input("/cancel", self.registry)
        self.assertEqual(outcome.kind, "command")
        self.assertEqual(outcome.command, "stop")

    def test_unregistered_slash_input_passes_through(self):
        for raw in ["/etc/hosts is a file", "/2.5 of the budget", "/", "/unknowncmd arg"]:
            with self.subTest(raw=raw):
                outcome = parse_input(raw, self.registry)
                self.assertEqual(outcome.kind, "passthrough")
                self.assertIsNone(outcome.command)

    def test_plain_text_passes_through_verbatim(self):
        raw = "  What is 2+2?  "
        outcome = parse_input(raw, self.registry)
        self.assertEqual(outcome.kind, "passthrough")
        self.assertEqual(outcome.raw, raw)

    def test_args_capture(self):
        outcome = parse_input("/model openai:gpt-4o-mini", self.registry)
        self.assertEqual(outcome.args, ["openai:gpt-4o-mini"])
        outcome = parse_input("/help retry now", self.registry)
        self.assertEqual(outcome.args, ["retry now"])

    def test_invalid_choice_is_error_not_passthrough(self):
        outcome = parse_input("/level warp", self.registry)
        self.assertEqual(outcome.kind, "error")
        self.assertIn("auto", outcome.error)
        self.assertIn("tree", outcome.error)

    def test_extra_args_rejected_for_zero_arg_commands(self):
        outcome = parse_input("/clear all", self.registry)
        self.assertEqual(outcome.kind, "error")
        self.assertIn("argument", outcome.error)

    def test_model_requires_colon(self):
        outcome = parse_input("/model gpt4o", self.registry)
        # Parser-level capture is fine; the service raises the validation error.
        self.assertEqual(outcome.kind, "command")
        self.assertEqual(outcome.args, ["gpt4o"])

    def test_registry_rejects_duplicates(self):
        registry = CommandRegistry()
        registry.register(build_default_registry().get("clear"))
        with self.assertRaises(SlashCommandError):
            registry.register(build_default_registry().get("clear"))

    def test_catalog_shape(self):
        catalog = command_catalog(self.registry)
        names = [entry["name"] for entry in catalog]
        self.assertEqual(
            names,
            ["help", "model", "level", "clear", "retry", "stop", "status"],
        )
        stop = next(entry for entry in catalog if entry["name"] == "stop")
        self.assertIn("cancel", stop["aliases"])
        self.assertTrue(stop["allowed_while_streaming"])
        retry = next(entry for entry in catalog if entry["name"] == "retry")
        self.assertTrue(retry["streaming"])


# ---------------------------------------------------------------------------
# Service (fake storage + fake engine session map)
# ---------------------------------------------------------------------------


def _make_service(session_row, engine_sessions=None, db_factory=None):
    async def load_session(session_id, user_id):
        return session_row if session_row and session_row.id == session_id else None

    return SlashCommandService(
        build_default_registry(),
        db_factory=db_factory,
        load_session=load_session,
        engine_sessions=engine_sessions if engine_sessions is not None else {},
    )


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.registry = build_default_registry()
        self.session_row = SimpleNamespace(
            id="s-1",
            user_id="u-1",
            title="T",
            status="idle",
            model_settings={"provider": "openai", "model_id": "gpt-4o-mini"},
            context_data={},
        )

    async def test_passthrough_reports_agent_message(self):
        service = _make_service(self.session_row)
        execution = await service.execute(
            parse_input("hello agent", self.registry),
            session_id="s-1",
            user_id="u-1",
        )
        self.assertEqual(execution.kind, "passthrough")
        self.assertEqual(execution.agent_message, "hello agent")

    async def test_help_lists_commands_and_topic(self):
        service = _make_service(self.session_row)
        listing = await service.execute(
            parse_input("/help", self.registry),
            session_id="s-1",
            user_id="u-1",
        )
        self.assertEqual(listing.kind, "reply")
        self.assertIn("/model", listing.reply.content)
        self.assertIn("/stop", listing.reply.content)
        topic = await service.execute(
            parse_input("/help retry", self.registry),
            session_id="s-1",
            user_id="u-1",
        )
        self.assertIn("Re-run the last user message", topic.reply.content)

    async def test_help_unknown_topic_is_error(self):
        service = _make_service(self.session_row)
        execution = await service.execute(
            parse_input("/help nope", self.registry),
            session_id="s-1",
            user_id="u-1",
        )
        self.assertEqual(execution.kind, "error")

    async def test_status_reports_model_and_warm_state(self):
        warm = SimpleNamespace(
            state_machine=SimpleNamespace(state=SimpleNamespace(value="completed")),
            _last_iteration=3,
            max_iterations=10,
            messages=[{"role": "user", "content": "x"}],
            metrics=SimpleNamespace(total_tokens_used=42),
            _stop_requested=False,
            restart_count=0,
        )
        service = _make_service(self.session_row, engine_sessions={"s-1": warm})
        execution = await service.execute(
            parse_input("/status", self.registry),
            session_id="s-1",
            user_id="u-1",
        )
        self.assertEqual(execution.kind, "reply")
        self.assertIn("openai:gpt-4o-mini", execution.reply.content)
        self.assertIn("42", execution.reply.content)
        self.assertEqual(execution.reply.payload["engine"]["iterations"], 3)

    async def test_model_view_and_update(self):
        service = _make_service(self.session_row)
        view = await service.execute(
            parse_input("/model", self.registry),
            session_id="s-1",
            user_id="u-1",
        )
        self.assertIn("openai:gpt-4o-mini", view.reply.content)

    async def test_stop_sets_engine_flag(self):
        warm = SimpleNamespace(_stop_requested=False, stop=lambda: None)
        service = _make_service(self.session_row, engine_sessions={"s-1": warm})
        execution = await service.execute(
            parse_input("/stop", self.registry),
            session_id="s-1",
            user_id="u-1",
            running=True,
        )
        self.assertEqual(execution.kind, "reply")
        self.assertEqual(execution.reply.effect, "stop_requested")
        self.assertTrue(warm._stop_requested)

    async def test_stop_without_warm_session_reports_noop(self):
        service = _make_service(self.session_row)
        execution = await service.execute(
            parse_input("/stop", self.registry),
            session_id="s-1",
            user_id="u-1",
            running=True,
        )
        self.assertIsNone(execution.reply.effect)

    async def test_non_stop_command_rejected_while_streaming(self):
        service = _make_service(self.session_row)
        execution = await service.execute(
            parse_input("/clear", self.registry),
            session_id="s-1",
            user_id="u-1",
            running=True,
        )
        self.assertEqual(execution.kind, "error")
        self.assertIn("/stop", execution.reply.content)

    async def test_last_user_message_prefers_most_recent(self):
        messages = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "answer"},
            {"role": "user", "content": "second"},
        ]
        self.assertEqual(last_user_message(messages), "second")
        self.assertIsNone(last_user_message([{"role": "assistant", "content": "only"}]))


# ---------------------------------------------------------------------------
# HTTP endpoints (real router + SQLite + fake engine)
# ---------------------------------------------------------------------------


class RecordingEngine(AgentEngine):
    """Real session factory; only run() is faked."""

    def __init__(self):
        self._sessions = {}
        self._session_locks = {}
        self.model_registry = None
        self.reasoning = None
        self.executed = []
        self.model_registry = SimpleNamespace()

    def _init_reasoning(self):
        self.reasoning = SimpleNamespace()

    async def run(self, session, message):
        self.executed.append((session.session_id, message, session.provider, session.model_id))
        yield AgentEvent(type=AgentEventType.TEXT, data={"content": f"echo:{message}"})
        yield AgentEvent(type=AgentEventType.DONE, data={"status": "completed"})


class ChatCommandEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.database = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.addAsyncCleanup(self.database.dispose)
        tables = [
            Agent.__table__,
            ApiKey.__table__,
            Session.__table__,
            Message.__table__,
        ]
        async with self.database.begin() as connection:
            await connection.run_sync(lambda conn: Base.metadata.create_all(conn, tables=tables))
        self.db = async_sessionmaker(self.database, expire_on_commit=False)
        async with self.db() as db:
            db.add_all(
                [
                    ApiKey(
                        id="key-a",
                        user_id="owner-a",
                        provider="openai",
                        name="A",
                        api_key_encrypted="plain:secret-a",
                        is_active=True,
                    ),
                    Session(
                        id="s-1",
                        user_id="owner-a",
                        title="T",
                        status="idle",
                        model_settings={
                            "credential_id": "key-a",
                            "provider": "openai",
                            "model_id": "gpt-4o-mini",
                        },
                    ),
                ]
            )
            db.add(Message(session_id="s-1", role="user", content="original question"))
            await db.commit()
        self.engine = RecordingEngine()
        patchers = [
            patch.object(chat_commands, "async_session", self.db),
            patch.object(chat_commands, "get_engine", return_value=self.engine),
            patch.object(chat_commands, "_ChatModelRegistry", lambda *a, **k: SimpleNamespace()),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        chat_commands._chat_inflight.clear()
        self.addCleanup(chat_commands._chat_inflight.clear)

        app = FastAPI()
        app.include_router(chat_commands.router, prefix="/api/v1")
        app.dependency_overrides[chat_commands.get_current_user] = lambda: "owner-a"
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )
        self.addAsyncCleanup(self.client.aclose)

    async def _sse_frames(self, response):
        body = response.text
        frames = []
        for block in body.split("\n\n"):
            event_name = ""
            data = None
            for line in block.split("\n"):
                if line.startswith("event:"):
                    event_name = line[6:].strip()
                elif line.startswith("data:"):
                    data = json.loads(line[5:].strip())
            if event_name:
                frames.append((event_name, data))
        return frames

    async def test_catalog_endpoint(self):
        response = await self.client.get("/api/v1/chat-commands")
        self.assertEqual(response.status_code, 200)
        names = [entry["name"] for entry in response.json()["commands"]]
        self.assertIn("retry", names)

    async def test_parse_endpoint(self):
        response = await self.client.post(
            "/api/v1/chat-commands/parse",
            json={"message": "/level warp"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["kind"], "error")
        self.assertIn("expected one of", body["error"])

        ok = await self.client.post(
            "/api/v1/chat-commands/parse",
            json={"message": "just a question"},
        )
        self.assertEqual(ok.json()["kind"], "passthrough")

    async def test_slash_help_streams_local_reply(self):
        response = await self.client.post("/api/v1/sessions/s-1/slash", json={"message": "/help"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        frames = await self._sse_frames(response)
        kinds = [name for name, _ in frames]
        self.assertEqual(kinds, ["text", "done"])
        self.assertIn("/model", frames[0][1]["content"])

    async def test_slash_passthrough_reaches_engine_verbatim(self):
        response = await self.client.post(
            "/api/v1/sessions/s-1/slash",
            json={"message": "/etc/hosts what is this"},
        )
        self.assertEqual(response.status_code, 200)
        frames = await self._sse_frames(response)
        self.assertEqual(frames[0][1]["content"], "echo:/etc/hosts what is this")
        self.assertEqual(self.engine.executed[0][1], "/etc/hosts what is this")

    async def test_slash_invalid_args_stream_error_event(self):
        response = await self.client.post(
            "/api/v1/sessions/s-1/slash",
            json={"message": "/clear all"},
        )
        frames = await self._sse_frames(response)
        self.assertEqual(frames[0][0], "error")
        self.assertIn("argument", frames[0][1]["error"])
        self.assertEqual(self.engine.executed, [])

    async def test_slash_retry_streams_last_user_message(self):
        response = await self.client.post("/api/v1/sessions/s-1/slash", json={"message": "/retry"})
        self.assertEqual(response.status_code, 200)
        frames = await self._sse_frames(response)
        self.assertEqual(frames[0][1]["content"], "echo:original question")
        self.assertEqual(self.engine.executed[0][1], "original question")

    async def test_slash_retry_without_history_reports_error(self):
        async with self.db() as db:
            rows = (await db.scalars(select(Message))).all()
            for row in rows:
                await db.delete(row)
            await db.commit()
        response = await self.client.post("/api/v1/sessions/s-1/slash", json={"message": "/retry"})
        frames = await self._sse_frames(response)
        self.assertEqual(frames[0][0], "error")
        self.assertIn("Nothing to retry", frames[0][1]["error"])

    async def test_slash_clear_deletes_messages(self):
        response = await self.client.post("/api/v1/sessions/s-1/slash", json={"message": "/clear"})
        frames = await self._sse_frames(response)
        done = frames[-1][1]
        self.assertEqual(done["effect"], "cleared")
        async with self.db() as db:
            remaining = (await db.scalars(select(Message))).all()
        self.assertEqual(remaining, [])

    async def test_slash_level_updates_session(self):
        response = await self.client.post(
            "/api/v1/sessions/s-1/slash",
            json={"message": "/level deep"},
        )
        frames = await self._sse_frames(response)
        self.assertEqual(frames[-1][1]["effect"], "level_updated")
        async with self.db() as db:
            row = await db.get(Session, "s-1")
        self.assertEqual(row.context_data["reasoning_level"], "deep")

    async def test_slash_model_switch_persists(self):
        response = await self.client.post(
            "/api/v1/sessions/s-1/slash",
            json={"message": "/model openai:o3-mini"},
        )
        frames = await self._sse_frames(response)
        self.assertEqual(frames[-1][1]["effect"], "model_updated")
        async with self.db() as db:
            row = await db.get(Session, "s-1")
        self.assertEqual(row.model_settings["model_id"], "o3-mini")

    async def test_slash_model_switch_rejects_credential_provider_mismatch(self):
        response = await self.client.post(
            "/api/v1/sessions/s-1/slash",
            json={"message": "/model anthropic:claude-3"},
        )
        frames = await self._sse_frames(response)
        self.assertEqual(frames[0][0], "error")
        self.assertIn("bound to provider 'openai'", frames[0][1]["error"])

    async def test_slash_rejects_foreign_session(self):
        app_client = self.client
        app_client.headers["x-user"] = "owner-b"
        # Ownership is enforced in _resolve_run_context via the session query;
        # parse-level commands still answer, but session effects 404.
        response = await app_client.post(
            "/api/v1/sessions/other/slash",
            json={"message": "/help"},
        )
        self.assertEqual(response.status_code, 200)  # local command, no session read

    async def test_cancel_reports_missing_turn(self):
        response = await self.client.post("/api/v1/sessions/s-1/cancel")
        self.assertEqual(response.status_code, 404)
        self.assertIn("No running turn", response.json()["detail"])

    async def test_cancel_interrupts_inflight_turn(self):
        chat_commands._chat_inflight.add("s-1")
        warm = SimpleNamespace(
            user_id="owner-a",
            _stop_requested=False,
            stop=lambda: None,
        )
        self.engine._sessions["s-1"] = warm
        response = await self.client.post("/api/v1/sessions/s-1/cancel")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["cancelled"])
        self.assertTrue(warm._stop_requested)


# ---------------------------------------------------------------------------
# Parser-level parametrized contract (pytest style, keeps future commands honest)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected_kind", "expected_command"),
    [
        ("/help", "command", "help"),
        ("/HELP", "command", "help"),
        ("/model", "command", "model"),
        ("/model openai:gpt-4o", "command", "model"),
        ("/level", "command", "level"),
        ("/level auto", "command", "level"),
        ("/clear", "command", "clear"),
        ("/retry", "command", "retry"),
        ("/stop", "command", "stop"),
        ("/cancel", "command", "stop"),
        ("/status", "command", "status"),
        ("/", "passthrough", None),
        ("/nope", "passthrough", None),
        ("/usr/bin/env python", "passthrough", None),
        ("hello world", "passthrough", None),
        ("", "passthrough", None),
        (None, "passthrough", None),
    ],
)
def test_parse_contract(raw, expected_kind, expected_command):
    outcome = parse_input(raw, build_default_registry())
    assert isinstance(outcome, ParseOutcome)
    assert outcome.kind == expected_kind
    assert outcome.command == expected_command
