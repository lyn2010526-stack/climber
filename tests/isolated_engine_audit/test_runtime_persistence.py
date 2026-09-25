"""Isolated unittest: real temporary SQLite, scripted LLM and mocked tools.

No provider requests, credentials, shared database or pytest conftest are used.
Run: python3 -m unittest discover -s tests/isolated_engine_audit -v
"""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import AgentEventType, ChatResult
from app.core.agent_engine import AgentEngine
from app.core.checkpoint import CheckpointData, InMemoryCheckpointStore, SQLiteCheckpointStore
from app.core.engine.run_storage import RunStorage
from app.core.engine.session_runner import merge_stream_chunk, response_usage
from app.core.recovery import RecoveryManager
from app.core.session import AgentSession, SessionConfig
from app.middleware.metrics import (ACTIVE_SESSIONS, AGENT_RUN_TOTAL, TOKEN_USAGE,
                                    TOOL_CALL_LATENCY, TOOL_CALL_TOTAL)
from app.storage import Base
from app.storage.database import Agent, CheckpointRecord, Message, Session, Turn, UsageLog
from app.storage.models_cost import CostRecord


def reply(content="answer", total=7, usage=None, tools=None):
    result = ChatResult(content=content, tokens_used=total, tool_calls=tools or [])
    if usage is not None:
        result.usage = usage
    return result


class ScriptedModel:
    """An explicit fake model; no network or real LLM is exercised."""

    def __init__(self, responses, streaming=False):
        self.responses = iter(responses)
        self.capabilities = SimpleNamespace(streaming=streaming, max_tokens=100000)
        self.seen = []

    async def chat(self, messages, **kwargs):
        self.seen.append(list(messages))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response

    async def stream_chat(self, messages, **kwargs):
        self.seen.append(list(messages))
        for chunk in next(self.responses):
            if isinstance(chunk, Exception):
                raise chunk
            yield chunk


class RuntimePersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="engine-audit-")
        self.db_engine = create_async_engine("sqlite+aiosqlite:///" + str(Path(self.tmp.name) / "isolated.db"))

        @event.listens_for(self.db_engine.sync_engine, "connect")
        def foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

        self.factory = async_sessionmaker(self.db_engine, expire_on_commit=False)
        tables = [model.__table__ for model in (Agent, Session, Turn, Message, UsageLog, CheckpointRecord, CostRecord)]
        async with self.db_engine.begin() as connection:
            await connection.run_sync(lambda conn: Base.metadata.create_all(conn, tables=tables))
        self.patches = [
            patch("app.storage.async_session", self.factory),
            patch("app.storage.engine", self.db_engine),
            patch("app.core.checkpoint.async_session", self.factory),
            patch.object(AgentEngine, "_init_sandbox", lambda engine: setattr(engine, "sandbox", None)),
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
        ]
        for item in self.patches:
            item.start()
        self.active = ACTIVE_SESSIONS._value.get()

    async def asyncTearDown(self):
        for item in reversed(self.patches):
            item.stop()
        await self.db_engine.dispose()
        self.tmp.cleanup()
        self.assertEqual(ACTIVE_SESSIONS._value.get(), self.active)

    def engine(self, model):
        engine = AgentEngine(model_registry=SimpleNamespace(get_or_create=lambda **kwargs: model),
                             tool_registry=Mock(), run_store=RunStorage(self.factory))
        engine.permission_overlay = None
        engine.agent_mode = None
        return engine

    def session(self, sid="session", **kwargs):
        return AgentSession(SessionConfig(session_id=sid, user_id="audit-user", agent_id="",
                                          provider="scripted-test", model_id="fake-model", **kwargs))

    async def rows(self, model):
        async with self.factory() as db:
            return list((await db.execute(select(model))).scalars())

    async def test_default_store_is_sqlite(self):
        self.assertIsInstance(self.engine(ScriptedModel([]))._checkpoints, SQLiteCheckpointStore)

    async def test_success_commits_before_done_and_writes_reported_usage(self):
        result = reply(usage={"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7})
        engine = self.engine(ScriptedModel([result]))
        session = self.session()
        async for item in engine.run(session, "hello"):
            if item.type == AgentEventType.DONE:
                self.assertEqual((await self.rows(Turn))[0].status, "completed")
                self.assertEqual(item.data["tokens_used"], 7)
        turn = (await self.rows(Turn))[0]
        usage = (await self.rows(UsageLog))[0]
        self.assertEqual((usage.prompt_tokens, usage.completion_tokens, usage.total_tokens), (4, 3, 7))
        self.assertEqual(turn.result, "answer")
        self.assertIsNotNone(turn.completed_at)
        self.assertEqual((await self.rows(Session))[0].total_tokens, 7)
        checkpoint = await SQLiteCheckpointStore().get(None, turn.checkpoint_id)
        self.assertEqual(checkpoint.status, "completed")
        self.assertEqual(checkpoint.metadata["thread_id"], turn.id)

    async def test_unknown_cost_is_explicit_without_fabricated_record(self):
        output = await self.engine(ScriptedModel([reply()])).run_agent(self.session(), "hi")
        turn = (await self.rows(Turn))[0]
        self.assertEqual(output["cost_status"], "unknown")
        call = turn.metadata_["model_calls"][0]
        self.assertIsNone(call["cost"])
        self.assertIsNone(call["usage"]["prompt_tokens"])
        self.assertIn("completion_tokens", call["unknown_usage_fields"])
        self.assertEqual(call["usage"]["total_tokens"], 7)
        self.assertEqual(call["usage_log_status"], "incomplete_usage")
        self.assertEqual(await self.rows(UsageLog), [])
        self.assertEqual(await self.rows(CostRecord), [])

    async def test_explicit_model_cost_writes_cost_record(self):
        # Deliberately synthetic model-supplied billing data, not real prices.
        result = reply(usage={"prompt_tokens": 4, "completion_tokens": 3})
        result.input_cost, result.output_cost, result.total_cost = 0.04, 0.03, 0.07
        output = await self.engine(ScriptedModel([result])).run_agent(self.session(), "hi")
        costs = await self.rows(CostRecord)
        self.assertEqual(len(costs), 1)
        self.assertEqual(costs[0].total_cost, 0.07)
        self.assertEqual(costs[0].id, (await self.rows(UsageLog))[0].id)
        self.assertEqual(output["cost_status"], "known")

    async def test_invalid_model_cost_remains_unknown(self):
        result = reply()
        result.input_cost, result.output_cost, result.total_cost = 1, 2, 99
        await self.engine(ScriptedModel([result])).run_agent(self.session(), "hi")
        self.assertEqual(await self.rows(CostRecord), [])
        self.assertEqual((await self.rows(Turn))[0].metadata_["cost_status"], "unknown")

    async def test_no_usage_does_not_create_fake_usage(self):
        await self.engine(ScriptedModel([reply(total=0)])).run_agent(self.session(), "hi")
        self.assertEqual(await self.rows(UsageLog), [])
        self.assertEqual((await self.rows(Turn))[0].metadata_["usage_status"], "unknown")

    async def test_stream_deltas_and_final_snapshot_are_not_duplicated(self):
        chunks = [ChatResult(content="ha", accumulated_content="ha"),
                  ChatResult(content="ha", accumulated_content="haha"),
                  ChatResult(content="haha", accumulated_content="haha", tokens_used=9)]
        output = await self.engine(ScriptedModel([chunks], True)).run_agent(self.session(), "hi")
        self.assertEqual(output["output"], "haha")
        messages = await self.rows(Message)
        self.assertEqual([row.content for row in messages if row.role == "assistant"], ["haha"])
        self.assertEqual((await self.rows(Turn))[0].metadata_["model_calls"][0]["usage"]["total_tokens"], 9)
        self.assertEqual(await self.rows(UsageLog), [])

    async def test_repeated_plain_deltas_are_preserved(self):
        chunks = [reply("ha", 0), reply("ha", 0)]
        output = await self.engine(ScriptedModel([chunks], True)).run_agent(self.session(), "hi")
        self.assertEqual(output["output"], "haha")

    async def test_stream_usage_dictionary_is_normalized(self):
        chunks = [reply("answer", 0), reply("", 0, {"input_tokens": 5, "output_tokens": 2})]
        output = await self.engine(ScriptedModel([chunks], True)).run_agent(self.session(), "hi")
        self.assertEqual(output["tokens_used"], 7)
        usage = (await self.rows(UsageLog))[0]
        self.assertEqual((usage.prompt_tokens, usage.completion_tokens), (5, 2))

    async def test_failure_sets_session_and_turn_and_metrics(self):
        counter = AGENT_RUN_TOTAL.labels(provider="scripted-test", model_id="fake-model", status="failed")
        before = counter._value.get()
        output = await self.engine(ScriptedModel([RuntimeError("scripted failure")])).run_agent(self.session(), "hi")
        self.assertEqual(output["status"], "failed")
        self.assertEqual(output["error"], "scripted failure")
        self.assertEqual((await self.rows(Session))[0].status, "failed")
        self.assertEqual((await self.rows(Turn))[0].error, "scripted failure")
        self.assertEqual(counter._value.get() - before, 1)

    async def test_early_stream_close_is_cancelled_and_balances_gauge(self):
        engine = self.engine(ScriptedModel([[reply("partial")]], True))
        events = engine.run(self.session(), "hi")
        await anext(events)
        self.assertEqual(ACTIVE_SESSIONS._value.get(), self.active + 1)
        await events.aclose()
        self.assertEqual((await self.rows(Turn))[0].status, "stopped")
        self.assertEqual((await self.rows(Session))[0].status, "stopped")

    async def test_task_cancellation_balances_gauge(self):
        entered = asyncio.Event()
        model = ScriptedModel([])

        async def blocked(**kwargs):
            entered.set()
            await asyncio.Event().wait()

        model.chat = blocked
        task = asyncio.create_task(self.engine(model).run_agent(self.session(), "hi"))
        await asyncio.wait_for(entered.wait(), 3)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual((await self.rows(Turn))[0].status, "stopped")

    async def test_empty_response_limit_is_failure(self):
        output = await self.engine(ScriptedModel([reply("", 0)])).run_agent(self.session(max_iterations=1), "hi")
        self.assertEqual(output["status"], "max_iterations_reached")
        self.assertEqual((await self.rows(Turn))[0].status, "failed")

    async def test_next_run_creates_new_turn_and_preserves_total_tokens(self):
        engine = self.engine(ScriptedModel([reply(total=3), reply(total=8)]))
        session = self.session()
        first = await engine.run_agent(session, "one")
        second = await engine.run_agent(session, "two")
        self.assertEqual((first["tokens_used"], second["tokens_used"]), (3, 8))
        self.assertEqual(len(await self.rows(Turn)), 2)
        self.assertEqual((await self.rows(Session))[0].total_tokens, 11)

    async def test_checkpoint_round_trip_new_store_redacts_key(self):
        engine = self.engine(ScriptedModel([reply("test-key-marker")]))
        session = self.session(api_key="test-key-marker")
        await engine.run_agent(session, "hi")
        await self.db_engine.dispose()
        fresh = self.session(api_key="fresh-key")
        self.assertTrue(await self.engine(ScriptedModel([])).recover_session(fresh))
        self.assertEqual(fresh.api_key, "fresh-key")
        self.assertEqual(fresh.messages[-1]["content"], "[REDACTED]")
        self.assertEqual(fresh.status.value, "completed")
        for row in await self.rows(CheckpointRecord):
            payload = " ".join([row.messages, row.metadata_, row.channel_values, row.pending_writes])
            self.assertNotIn("test-key-marker", payload)

    async def test_store_redacts_nested_credential_fields(self):
        store = SQLiteCheckpointStore()
        cp = CheckpointData("s", [], 0, "processing", metadata={"api_key": "private"},
                            channel_values={"nested": {"authorization": "Bearer private"}})
        cid = await store.save(None, cp)
        restored = await store.get(None, cid)
        self.assertEqual(restored.metadata["api_key"], "[REDACTED]")
        self.assertEqual(restored.channel_values["nested"]["authorization"], "[REDACTED]")
        self.assertEqual(cp.metadata["api_key"], "private")

    async def test_latest_checkpoint_prefers_new_turn_not_larger_iteration(self):
        for store in (SQLiteCheckpointStore(), InMemoryCheckpointStore()):
            await store.save(None, CheckpointData("s", [], 9, "completed"), thread_id="old")
            new = await store.save(None, CheckpointData("s", [], 1, "processing"), thread_id="new")
            self.assertEqual((await store.get_latest(None, "s"))[1], new)
            self.assertEqual((await store.get_latest(None, "s", thread_id="old"))[0].iteration, 9)

    async def test_in_memory_snapshot_is_independent(self):
        store = InMemoryCheckpointStore()
        cp = CheckpointData("s", [{"role": "user", "content": "first"}], 1, "processing")
        cid = await store.save(None, cp)
        cp.messages.append({"role": "assistant", "content": "later"})
        loaded = await store.get(None, cid)
        self.assertEqual(len(loaded.messages), 1)
        loaded.messages.clear()
        self.assertEqual(len((await store.get(None, cid)).messages), 1)

    async def test_restore_then_run_continues_existing_turn_and_history(self):
        session = self.session()
        store = RunStorage(self.factory)
        await store.begin(session)
        cp = CheckpointData(session.session_id, [{"role": "user", "content": "original"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "t1"}]},
            {"role": "tool", "content": "saved tool result", "tool_call_id": "t1"}], 2, "processing")
        await SQLiteCheckpointStore().save(None, cp, thread_id=session.current_turn_id)
        model = ScriptedModel([reply("resumed")])
        engine = self.engine(model)
        restored = self.session()
        self.assertTrue(await engine.recover_session(restored))
        output = await engine.run_agent(restored, "must not append this")
        self.assertEqual(output["output"], "resumed")
        self.assertEqual([m["content"] for m in model.seen[0] if m["role"] == "user"], ["original"])
        self.assertEqual(restored._last_iteration, 3)
        self.assertEqual(len(await self.rows(Turn)), 1)
        self.assertEqual(restored.current_turn_id, session.current_turn_id)

    async def test_pending_tool_side_effects_block_automatic_restore(self):
        cp = CheckpointData("s", [], 1, "processing", pending_writes=[
            {"channel": "tools", "value": {}, "write_id": "t", "status": "pending"}])
        await SQLiteCheckpointStore().save(None, cp)
        with self.assertRaisesRegex(ValueError, "pending writes"):
            await self.engine(ScriptedModel([])).recover_session(self.session("s"))

    async def test_discovery_reports_recoverable_not_resumed(self):
        await SQLiteCheckpointStore().save(None, CheckpointData("s", [], 1, "processing"))
        items = await RecoveryManager().auto_recover()
        self.assertEqual(items[0]["status"], "recoverable")
        self.assertEqual(await self.rows(Turn), [])

    async def test_metrics_increment_using_real_counts(self):
        total = TOKEN_USAGE.labels(provider="scripted-test", model_id="fake-model", type="total")
        run = AGENT_RUN_TOTAL.labels(provider="scripted-test", model_id="fake-model", status="completed")
        before_total, before_run = total._value.get(), run._value.get()
        await self.engine(ScriptedModel([reply(total=17)])).run_agent(self.session(), "hi")
        self.assertEqual(total._value.get() - before_total, 17)
        self.assertEqual(run._value.get() - before_run, 1)

    async def test_tools_metrics_and_multicall_usage(self):
        tool_call = {"id": "call1", "type": "function", "function": {"name": "fake_tool", "arguments": "{}"}}
        model = ScriptedModel([reply("", 4, {"prompt_tokens": 3, "completion_tokens": 1}, [tool_call]),
                               reply("done", 9, {"prompt_tokens": 5, "completion_tokens": 4})])
        engine = self.engine(model)
        engine._validate_tool_call = Mock(return_value=(True, ""))
        result = SimpleNamespace(tool_name="fake_tool", tool_call_id="call1", success=True,
                                 duration_ms=250, result="ok", error="", arguments={})
        executor = SimpleNamespace(execute_all=AsyncMock(return_value=[result]))
        count = TOOL_CALL_TOTAL.labels(tool_name="fake_tool", status="success")
        latency = TOOL_CALL_LATENCY.labels(tool_name="fake_tool")
        before_count, before_latency = count._value.get(), latency._sum.get()
        with patch("app.core.agent_engine.ParallelToolExecutor", return_value=executor):
            output = await engine.run_agent(self.session(), "hi")
        self.assertEqual(output["tokens_used"], 13)
        self.assertEqual(len(await self.rows(UsageLog)), 2)
        self.assertEqual(count._value.get() - before_count, 1)
        self.assertAlmostEqual(latency._sum.get() - before_latency, 0.25)
        pending = [row for row in await self.rows(CheckpointRecord) if json.loads(row.pending_writes)]
        self.assertEqual(len(pending), 1)

    async def test_error_event_is_emitted_after_failed_turn_commit(self):
        engine = self.engine(ScriptedModel([RuntimeError("failure")]))
        async for item in engine.run(self.session(), "hi"):
            if item.type == AgentEventType.ERROR:
                self.assertEqual((await self.rows(Turn))[0].status, "failed")
                self.assertEqual(ACTIVE_SESSIONS._value.get(), self.active)

    async def test_partial_stream_failure_keeps_reported_usage(self):
        chunks = [reply("partial", 4), RuntimeError("stream failed")]
        session = self.session()
        result = await self.engine(ScriptedModel([chunks], True)).run_agent(session, "hi")
        self.assertEqual(result["status"], "failed")
        turn = (await self.rows(Turn))[0]
        self.assertEqual(turn.metadata_["model_calls"][0]["usage"]["total_tokens"], 4)
        self.assertEqual(await self.rows(UsageLog), [])
        self.assertFalse(turn.metadata_["model_calls"][0]["response_complete"])
        self.assertEqual(turn.metadata_["usage_status"], "unknown")
        self.assertEqual(len(session.metrics.llm_call_durations), 1)

    async def test_close_after_text_records_observed_usage_before_returning(self):
        engine = self.engine(ScriptedModel([[reply("partial", 6)]], True))
        events = engine.run(self.session(), "hi")
        async for item in events:
            if item.type == AgentEventType.TEXT:
                break
        await events.aclose()
        self.assertEqual((await self.rows(Turn))[0].status, "stopped")
        self.assertEqual((await self.rows(Turn))[0].tokens_used, 6)
        self.assertEqual(await self.rows(UsageLog), [])
        self.assertEqual(ACTIVE_SESSIONS._value.get(), self.active)

    async def test_model_error_finish_reason_is_failure(self):
        error = reply("provider error", 5)
        error.finish_reason = "error"
        result = await self.engine(ScriptedModel([error])).run_agent(self.session(), "hi")
        self.assertEqual(result["status"], "failed")
        self.assertEqual((await self.rows(Turn))[0].status, "failed")

    async def test_checkpoint_save_failure_does_not_emit_done(self):
        engine = self.engine(ScriptedModel([reply()]))
        engine._checkpoints.save = AsyncMock(side_effect=RuntimeError("checkpoint unavailable"))
        events = []
        with self.assertRaisesRegex(RuntimeError, "checkpoint unavailable"):
            async for item in engine.run(self.session(), "hi"):
                events.append(item.type)
        self.assertNotIn(AgentEventType.DONE, events)
        self.assertEqual((await self.rows(Turn))[0].status, "failed")

    async def test_final_transaction_failure_does_not_emit_done(self):
        engine = self.engine(ScriptedModel([reply()]))
        engine._run_store.finish = AsyncMock(side_effect=RuntimeError("commit failed"))
        events = []
        with self.assertRaisesRegex(RuntimeError, "commit failed"):
            async for item in engine.run(self.session(), "hi"):
                events.append(item.type)
        self.assertNotIn(AgentEventType.DONE, events)
        self.assertEqual(ACTIVE_SESSIONS._value.get(), self.active)

    async def test_failed_checkpoint_does_not_restore_as_completed(self):
        await SQLiteCheckpointStore().save(None, CheckpointData("s", [], 3, "failed"))
        session = self.session("s")
        self.assertTrue(await self.engine(ScriptedModel([])).recover_session(session))
        self.assertEqual(session.status.value, "failed")
        self.assertFalse(session._resume_interrupted)

    async def test_resilience_accumulator_uses_same_snapshot_rules(self):
        chunks = [ChatResult(content="one", accumulated_content="one"),
                  ChatResult(content="one", accumulated_content="one", tokens_used=3)]
        engine = self.engine(ScriptedModel([]))
        result = await engine._stream_accumulate(ScriptedModel([chunks], True), [], [])
        self.assertEqual(result.content, "one")
        result = await engine._stream_chat(ScriptedModel([chunks], True), self.session(), [])
        self.assertEqual(result.content, "one")

    async def test_nonstream_response_usage_populates_message_tokens(self):
        result = reply(total=0, usage={"input_tokens": 5, "output_tokens": 3})
        session = self.session()
        output = await self.engine(ScriptedModel([result])).run_agent(session, "hi")
        self.assertEqual(output["tokens_used"], 8)
        self.assertEqual(session.metrics.total_tokens_used, 8)
        assistant = [row for row in await self.rows(Message) if row.role == "assistant"][0]
        self.assertEqual(assistant.tokens, 8)

    async def test_busy_session_does_not_create_second_turn(self):
        engine = self.engine(ScriptedModel([reply()]))
        session = self.session()
        first = engine.run(session, "first")
        await anext(first)
        second = [item async for item in engine.run(session, "second")]
        self.assertEqual(second[0].type, AgentEventType.ERROR)
        self.assertEqual(len(await self.rows(Turn)), 1)
        await first.aclose()


class ResponseContractTests(unittest.TestCase):
    def test_zero_usage_is_known_only_when_explicit(self):
        self.assertIsNone(response_usage(ChatResult())["total_tokens"])
        self.assertEqual(response_usage(reply(total=0, usage={"total_tokens": 0}))["total_tokens"], 0)

    def test_partial_usage_is_not_guessed(self):
        usage = response_usage(reply(total=0, usage={"prompt_tokens": 4}))
        self.assertEqual(usage, {"prompt_tokens": 4, "completion_tokens": None, "total_tokens": None})

    def test_diverging_snapshot_fails_explicitly(self):
        result = ChatResult(content="old")
        with self.assertRaisesRegex(ValueError, "diverged"):
            merge_stream_chunk(result, ChatResult(accumulated_content="new"))

    def test_distinct_complete_tool_calls_are_retained(self):
        calls = []
        for name in ("a", "b"):
            AgentEngine._accumulate_stream_tool_calls(calls, [{"id": name,
                "function": {"name": name, "arguments": {"x": 1}}}])
        self.assertEqual([call["id"] for call in calls], ["a", "b"])

    def test_indexed_tool_argument_deltas_are_joined(self):
        calls = []
        AgentEngine._accumulate_stream_tool_calls(calls, [{"index": 0, "id": "a",
            "function": {"name": "tool", "arguments": '{"x":'}}])
        AgentEngine._accumulate_stream_tool_calls(calls, [{"index": 0,
            "function": {"arguments": '1}'}}])
        self.assertEqual(json.loads(calls[0]["function"]["arguments"]), {"x": 1})


if __name__ == "__main__":
    unittest.main()
