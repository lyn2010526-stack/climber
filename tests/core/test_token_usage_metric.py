"""Token usage metric tests.

`TOKEN_USAGE` (app/middleware/metrics.py) is a Prometheus counter labelled
provider/model_id/type, declared and exported but never incremented anywhere in
app/. Every other counter in that module has a real write point, so
`token_usage_total` appeared on /metrics as a permanent zero and token spend
was invisible in monitoring.

These tests pin that recording a model result actually moves the counter, and
that a missing or malformed usage block does not raise - a metrics path must
never break a request.
"""

from __future__ import annotations

import pytest


def _reset_counter() -> None:
    """Zero every labelled child so one test cannot influence the next."""
    from app.middleware.metrics import TOKEN_USAGE

    for child in TOKEN_USAGE._metrics.values():
        value = getattr(child, "_value", None)
        if value is not None:
            value.set(0)


@pytest.fixture(autouse=True)
def clean_counter():
    _reset_counter()
    yield
    _reset_counter()


def test_recording_usage_increments_the_counter() -> None:
    from app.middleware.metrics import record_token_usage

    before = _counter_value()

    record_token_usage(
        provider="anthropic",
        model_id="claude-x",
        prompt_tokens=100,
        completion_tokens=20,
    )

    assert _counter_value() == before + 120


def test_total_only_usage_is_recorded() -> None:
    from app.middleware.metrics import record_token_usage

    before = _counter_value()

    record_token_usage(provider="openai", model_id="gpt-x", total_tokens=50)

    assert _counter_value() == before + 50


def test_missing_usage_is_a_no_op() -> None:
    """A response without usage must not raise."""
    from app.middleware.metrics import record_token_usage

    before = _counter_value()

    record_token_usage(provider="openai", model_id="gpt-x", usage={})

    assert _counter_value() == before


def test_malformed_usage_values_are_ignored() -> None:
    from app.middleware.metrics import record_token_usage

    before = _counter_value()

    record_token_usage(
        provider="openai",
        model_id="gpt-x",
        usage={"prompt_tokens": "not-a-number", "completion_tokens": None},
    )

    assert _counter_value() == before


def test_negative_values_are_ignored() -> None:
    from app.middleware.metrics import record_token_usage

    before = _counter_value()

    record_token_usage(provider="openai", model_id="gpt-x", total_tokens=-5)

    assert _counter_value() == before


def test_a_chat_result_can_be_recorded_directly() -> None:
    """The engine has a ChatResult in hand; it should not have to reshape it."""
    from app.core import ChatResult
    from app.middleware.metrics import record_chat_result

    before = _counter_value()
    result = ChatResult(
        content="hi",
        usage={"prompt_tokens": 10, "completion_tokens": 5},
    )

    record_chat_result(result, provider="anthropic", model_id="claude-x")

    assert _counter_value() == before + 15


def _counter_value() -> float:
    """Total across every label combination, read through the public API."""
    from app.middleware.metrics import TOKEN_USAGE

    total = 0.0
    for metric in TOKEN_USAGE.collect():
        for sample in metric.samples:
            if sample.name == "token_usage_total":
                total += sample.value
    return total


def test_the_engine_records_usage_from_a_real_call() -> None:
    """The counter must be wired into the engine, not just defined."""
    from app.core import ChatResult
    from app.core.agent_engine import _record_usage
    from app.core.session import AgentSession

    class FakeAdapter:
        provider = "anthropic"
        _model_id = "claude-x"

    before = _counter_value()
    session = AgentSession(session_id="s", agent_id="a", user_id="u", model_id="claude-x")
    result = ChatResult(usage={"prompt_tokens": 7, "completion_tokens": 3})

    _record_usage(result, FakeAdapter(), session)

    assert _counter_value() == before + 10


def test_recording_a_none_result_is_safe() -> None:
    from app.core.agent_engine import _record_usage
    from app.core.session import AgentSession

    class FakeAdapter:
        provider = "openai"

    session = AgentSession(session_id="s", agent_id="a", user_id="u")
    before = _counter_value()

    _record_usage(None, FakeAdapter(), session)

    assert _counter_value() == before
