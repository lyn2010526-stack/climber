"""Scripted adapter tests; these do not measure real-model quality."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.core import ChatResult
from app.core.instruction.understanding import InstructionUnderstanding
from app.core.prompt_optimizer.config import OptimizerConfig
from app.core.prompt_optimizer.service import clear_reference, maybe_optimize_instruction
from app.core.prompt_optimizer.templates import ANALYSIS_TEMPLATE


@pytest.fixture
def fixture(monkeypatch):
    monkeypatch.setenv("USER_PROMPT_OPT_MODE", "auto")
    original = "优化它, 保留 {{target}}, 禁止部署"
    session = SimpleNamespace(
        session_id="s",
        mode="act",
        provider="openai",
        model_id="fake",
        api_key="project-test-key",
        base_url="https://project.example/v1",
        messages=[{"role": "user", "content": original}],
    )
    adapter = SimpleNamespace(
        chat=AsyncMock(
            return_value=ChatResult(
                content=json.dumps(
                    {
                        "evidence": [original],
                        "questions": ["它具体指什么?"],
                        "missing_information": True,
                    },
                    ensure_ascii=False,
                ),
                finish_reason="stop",
            )
        )
    )
    engine = SimpleNamespace(
        model_registry=SimpleNamespace(get_or_create=Mock(return_value=adapter))
    )
    return engine, session, adapter, original


@pytest.mark.asyncio
async def test_reference_preserves_raw_constraints_placeholders_and_project_credentials(fixture):
    engine, session, adapter, original = fixture
    await maybe_optimize_instruction(engine, session, original)
    assert session.messages[-1] == {"role": "user", "content": original}
    reference = session.messages[0]
    assert reference["source"] == "prompt_optimizer"
    assert "{{target}}" in reference["content"]
    assert "禁止部署" in reference["content"]
    payload = json.loads(reference["content"].split("\n")[-1])
    assert payload["original"] == original
    assert payload["clarification_required"] is True
    assert "它具体指什么?" in payload["questions"]
    engine.model_registry.get_or_create.assert_called_once_with(
        provider="openai",
        model_id="fake",
        api_key="project-test-key",
        base_url="https://project.example/v1",
    )
    kwargs = adapter.chat.call_args.kwargs
    assert kwargs["tools"] is None
    assert kwargs["max_tokens"] == 512
    assert kwargs["temperature"] == 0
    assert kwargs["messages"][0]["content"] == ANALYSIS_TEMPLATE.render()
    assert json.loads(kwargs["messages"][1]["content"])["original"] == original


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "original", "autonomous"),
    [
        ("off", "优化它", False),
        ("always", "优化它", False),
        ("auto", "实现二分查找, 必须返回索引", False),
        ("auto", "", False),
        ("auto", "x" * 2001, False),
        ("auto", "优化它", True),
    ],
)
async def test_skip_without_model_call(fixture, monkeypatch, mode, original, autonomous):
    engine, session, adapter, _ = fixture
    monkeypatch.setenv("USER_PROMPT_OPT_MODE", mode)
    session.mode = "autonomous" if autonomous else "act"
    session.messages = [{"role": "user", "content": original}]
    await maybe_optimize_instruction(engine, session, original)
    engine.model_registry.get_or_create.assert_not_called()
    adapter.chat.assert_not_awaited()
    assert session.messages == [{"role": "user", "content": original}]


@pytest.mark.asyncio
async def test_low_confidence_alone_triggers(fixture, monkeypatch):
    engine, session, adapter, original = fixture
    monkeypatch.setattr(
        "app.core.prompt_optimizer.service.understand_instruction",
        lambda *_a, **_k: InstructionUnderstanding(original, original, confidence=0.2),
    )
    await maybe_optimize_instruction(engine, session, original)
    adapter.chat.assert_awaited_once()
    assert len(session.messages) == 2


@pytest.mark.asyncio
async def test_high_confidence_needs_clarification_triggers(fixture, monkeypatch):
    engine, session, adapter, original = fixture
    monkeypatch.setattr(
        "app.core.prompt_optimizer.service.understand_instruction",
        lambda *_a, **_k: InstructionUnderstanding(
            original, original, confidence=0.99, progress="needs_clarification"
        ),
    )
    await maybe_optimize_instruction(engine, session, original)
    adapter.chat.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [
        "",
        "not json",
        "[]",
        '{"evidence":[]}',
        '{"evidence":["发布到生产"],"questions":[],"missing_information":false}',
        '{"evidence":[3],"questions":[],"missing_information":false}',
        '{"evidence":["优化它"],"questions":"ask","missing_information":true}',
        '{"evidence":["优化它"],"questions":[],"missing_information":"yes"}',
        "x" * 4097,
    ],
)
async def test_invalid_or_scope_expanding_result_keeps_original(fixture, content):
    engine, session, adapter, original = fixture
    adapter.chat.return_value.content = content
    before = list(session.messages)
    await maybe_optimize_instruction(engine, session, original)
    assert session.messages == before
    adapter.chat.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("finish", ["length", "error", "offline", "tool_calls"])
async def test_unfinished_response_falls_back(fixture, finish):
    engine, session, adapter, original = fixture
    adapter.chat.return_value.finish_reason = finish
    await maybe_optimize_instruction(engine, session, original)
    assert len(session.messages) == 1


@pytest.mark.asyncio
async def test_missing_goal_and_missing_question_get_local_clarification(fixture):
    engine, session, adapter, _ = fixture
    session.messages[-1]["content"] = "继续"
    adapter.chat.return_value.content = json.dumps(
        {
            "evidence": ["继续"],
            "questions": [],
            "missing_information": True,
        }
    )
    await maybe_optimize_instruction(engine, session, "继续")
    payload = json.loads(session.messages[0]["content"].split("\n")[-1])
    assert payload["clarification_required"]
    assert "请说明这次操作要达成的主目标。" in payload["questions"]
    assert payload["evidence"] == ["继续"]


@pytest.mark.asyncio
async def test_model_reported_missing_info_always_gets_a_question(fixture, monkeypatch):
    engine, session, adapter, original = fixture
    monkeypatch.setattr(
        "app.core.prompt_optimizer.service.understand_instruction",
        lambda *_a, **_k: InstructionUnderstanding(original, original, confidence=0.2),
    )
    adapter.chat.return_value.content = json.dumps(
        {
            "evidence": [original],
            "questions": [],
            "missing_information": True,
        }
    )
    await maybe_optimize_instruction(engine, session, original)
    payload = json.loads(session.messages[0]["content"].split("\n")[-1])
    assert payload["clarification_required"]
    assert payload["questions"]


@pytest.mark.asyncio
async def test_exception_falls_back_without_logging_sensitive_error(fixture, monkeypatch):
    engine, session, adapter, original = fixture
    logger = Mock()
    monkeypatch.setattr("app.core.prompt_optimizer.service.logger", logger)
    adapter.chat.side_effect = RuntimeError("secret project key")
    await maybe_optimize_instruction(engine, session, original)
    assert len(session.messages) == 1
    logger.warning.assert_called_once_with("prompt_optimizer_degraded", error_type="RuntimeError")


@pytest.mark.asyncio
async def test_timeout_cancels_one_call_without_retry(fixture, monkeypatch):
    engine, session, adapter, original = fixture
    monkeypatch.setenv("USER_PROMPT_OPT_TIMEOUT_SECONDS", "0.01")
    cancelled = asyncio.Event()

    async def blocked(**kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    adapter.chat.side_effect = blocked
    await asyncio.wait_for(maybe_optimize_instruction(engine, session, original), timeout=1)
    assert cancelled.is_set()
    assert len(session.messages) == 1
    adapter.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_caller_cancellation_propagates(fixture):
    engine, session, adapter, original = fixture
    adapter.chat.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await maybe_optimize_instruction(engine, session, original)
    assert len(session.messages) == 1


@pytest.mark.asyncio
async def test_no_project_key_skips_registry_and_model(fixture):
    engine, session, adapter, original = fixture
    session.api_key = ""
    await maybe_optimize_instruction(engine, session, original)
    engine.model_registry.get_or_create.assert_not_called()
    adapter.chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_registry_failure_keeps_raw_request(fixture):
    engine, session, adapter, original = fixture
    engine.model_registry.get_or_create.side_effect = ValueError("unconfigured model")
    await maybe_optimize_instruction(engine, session, original)
    assert session.messages == [{"role": "user", "content": original}]
    adapter.chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_tool_response_is_rejected_even_with_valid_content(fixture):
    engine, session, adapter, original = fixture
    adapter.chat.return_value.tool_calls = [{"function": {"name": "deploy"}}]
    await maybe_optimize_instruction(engine, session, original)
    assert len(session.messages) == 1


@pytest.mark.asyncio
async def test_multimodal_user_content_is_untouched(fixture):
    engine, session, _, original = fixture
    content = [
        {"type": "text", "text": original},
        {"type": "image_url", "image_url": {"url": "https://project.example/image.png"}},
    ]
    session.messages[-1]["content"] = content
    await maybe_optimize_instruction(engine, session, original)
    assert session.messages[-1]["content"] is content
    assert session.messages[0]["source"] == "prompt_optimizer"


def test_only_owned_system_references_expire(fixture):
    _, session, _, original = fixture
    preserved = [
        {"role": "system", "content": "base"},
        {"role": "user", "content": original, "source": "prompt_optimizer"},
        {"role": "system", "content": "memory", "source": "memory"},
    ]
    session.messages = [
        *preserved,
        {"role": "system", "content": "old", "source": "prompt_optimizer"},
    ]
    clear_reference(session)
    assert session.messages == preserved


@pytest.mark.parametrize("value", ["nan", "inf", "-1", "garbage", "999999"])
def test_invalid_budget_settings_use_bounded_defaults(monkeypatch, value):
    for name in ("TIMEOUT_SECONDS", "MAX_TOKENS", "MAX_INPUT_CHARS", "CONFIDENCE_THRESHOLD"):
        monkeypatch.setenv("USER_PROMPT_OPT_" + name, value)
    config = OptimizerConfig.from_env()
    assert config.timeout_seconds == 5
    assert config.max_tokens == 512
    assert config.max_input_chars == 2000
    assert config.confidence_threshold == 0.45
