"""Run-locked wiring using scripted adapters and in-memory persistence hooks."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.core import AgentEvent, AgentEventType, ChatResult
from app.core.engine.runner import run_locked
from app.core.session import AgentSession, SessionConfig


def make_engine():
    adapter = SimpleNamespace(chat=AsyncMock(return_value=ChatResult(
        content=json.dumps({"evidence": ["优化它"], "questions": ["具体优化哪个对象?"],
                            "missing_information": True}, ensure_ascii=False),
        finish_reason="stop",
    )))
    engine = SimpleNamespace(model_registry=SimpleNamespace(get_or_create=Mock(return_value=adapter)))
    for name in ("_persist_message", "_archive_instruction", "_inject_memory_context",
                 "_inject_core_memory", "_inject_profile_context", "_save_checkpoint",
                 "_store_episodic_memory"):
        setattr(engine, name, AsyncMock())
    for name in ("_set_agent_mode", "_send_start_notification", "_make_parallel_executor",
                 "_trigger_memory_reflection", "_record_profile_outcome", "_tick_evolution"):
        setattr(engine, name, Mock())
    seen = []

    async def iteration(session, executor, compressor):
        seen.append(list(session.messages))
        yield AgentEvent(type=AgentEventType.TEXT, data={"content": "scripted"})

    engine._iteration_loop = iteration
    return engine, adapter, seen


@pytest.mark.asyncio
async def test_runner_injects_before_iteration_and_persists_verbatim_then_expires(monkeypatch):
    monkeypatch.setenv("USER_PROMPT_OPT_MODE", "auto")
    engine, adapter, seen = make_engine()
    session = AgentSession(SessionConfig(
        session_id="s", provider="openai", model_id="fake", api_key="project-key",
    ))
    events = [event async for event in run_locked(engine, session, "优化它")]
    assert events[-1].type == AgentEventType.DONE
    assert seen[0][-1]["content"] == "优化它"
    assert seen[0][-2]["source"] == "prompt_optimizer"
    assert engine._persist_message.call_args.kwargs["content"] == "优化它"
    engine._archive_instruction.assert_awaited_once_with(session, "优化它")
    adapter.chat.assert_awaited_once()
    await asyncio_collect(run_locked(engine, session, "实现二分查找, 必须返回索引"))
    assert not any(item.get("source") == "prompt_optimizer" for item in seen[-1])
    adapter.chat.assert_awaited_once()


async def asyncio_collect(iterator):
    return [event async for event in iterator]


@pytest.mark.asyncio
async def test_runner_failure_preserves_original_and_continues_facade(monkeypatch):
    monkeypatch.setenv("USER_PROMPT_OPT_MODE", "auto")
    engine, adapter, seen = make_engine()
    adapter.chat.side_effect = RuntimeError("scripted failure")
    session = AgentSession(SessionConfig(
        session_id="s", provider="openai", model_id="fake", api_key="project-key",
    ))
    events = await asyncio_collect(run_locked(engine, session, "优化它"))
    assert events[-1].type == AgentEventType.DONE
    assert seen == [[{"role": "user", "content": "优化它"}]]


@pytest.mark.asyncio
async def test_resume_keeps_existing_reference_and_skips_optimizer(monkeypatch):
    monkeypatch.setenv("USER_PROMPT_OPT_MODE", "auto")
    engine, adapter, seen = make_engine()
    session = AgentSession(SessionConfig(session_id="s"))
    session._resume_interrupted = True
    reference = {"role": "system", "content": "current", "source": "prompt_optimizer"}
    session.messages = [reference, {"role": "user", "content": "优化它"}]
    await asyncio_collect(run_locked(engine, session, "优化它"))
    adapter.chat.assert_not_awaited()
    engine._persist_message.assert_not_awaited()
    assert seen[0][0] == reference
