"""Coverage tests for app.core.compressor.

Strategies: truncate, sliding and summarize (with a fake async model),
plus the synchronous ``compress_with_budget`` helper.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core import CompressionStrategy, ContextConfig, MessageRole
from app.core.compressor import ContextCompressor, estimate_tokens


@dataclass
class FakeChatResult:
    content: str | None


class FakeModel:
    """Minimal async model exposing the ``chat`` entry point used by compressor."""

    def __init__(self, content: str | None = "summary", exc: Exception | None = None) -> None:
        self._content = content
        self._exc = exc
        self.calls: list[dict[str, Any]] = []

    async def chat(self, messages: list[dict[str, Any]], tools: Any = None) -> FakeChatResult:
        self.calls.append({"messages": messages, "tools": tools})
        if self._exc is not None:
            raise self._exc
        return FakeChatResult(content=self._content)


def _config(strategy: CompressionStrategy, keep: int = 2, max_tokens: int = 100) -> ContextConfig:
    return ContextConfig(
        max_tokens=max_tokens,
        compression_strategy=strategy,
        keep_recent_messages=keep,
    )


def _msgs(n: int, role: str = "user", content: str = "hello world") -> list[dict[str, Any]]:
    return [{"role": role, "content": content} for _ in range(n)]


# ── estimate_tokens ─────────────────────────────────────────────────────


def test_estimate_tokens_content_and_tool_calls() -> None:
    tool_call = {"id": "x" * 8}
    msgs = [
        {"role": "user", "content": "a" * 8},  # 2 tokens
        {"role": "assistant", "content": "", "tool_calls": [tool_call]},
    ]
    expected = 2 + len(str(tool_call)) // 4
    assert estimate_tokens(msgs) == expected
    assert estimate_tokens([]) == 0


def test_needs_compression() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.TRUNCATE, max_tokens=2))
    assert comp.needs_compression([{"content": "a" * 100}]) is True
    assert comp.needs_compression([{"content": "a"}]) is False


# ── compress dispatch ───────────────────────────────────────────────────


async def test_compress_unknown_strategy_returns_input_unchanged() -> None:
    cfg = ContextConfig(max_tokens=1, compression_strategy=CompressionStrategy.TRUNCATE)
    object.__setattr__(cfg, "compression_strategy", "no-such-strategy")
    comp = ContextCompressor(cfg)
    msgs = _msgs(5)
    assert await comp.compress(msgs, FakeModel()) is msgs


async def test_compress_truncate_dispatch() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.TRUNCATE, keep=2))
    out = await comp.compress(_msgs(6), FakeModel())
    assert out[0] == {"role": "user", "content": "hello world"}
    assert out[1]["content"] == "[Earlier conversation truncated for brevity]"
    assert len(out) == 4


async def test_compress_sliding_dispatch() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.SLIDING, keep=2))
    out = await comp.compress(_msgs(6), FakeModel())
    assert out[1]["content"] == "[Earlier messages truncated]"
    assert len(out) == 4


async def test_compress_summarize_dispatch() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.SUMMARIZE, keep=2))
    out = await comp.compress(_msgs(6), FakeModel(content="recap"))
    # no leading system message -> the summary is placed first
    assert out[0]["content"] == "[Summary of earlier conversation]\nrecap"
    assert out[0]["source"] == "compression_summary"
    assert out[0]["trust"] == "derived"
    assert out[0]["untrusted"] is True
    assert out[-2:] == _msgs(2)


# ── _truncate / _sliding edge cases ─────────────────────────────────────


def test_truncate_returns_input_when_short() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.TRUNCATE, keep=4))
    msgs = _msgs(5)  # len == keep + 1
    assert comp._truncate(msgs) is msgs


def test_truncate_shortens_long_history() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.TRUNCATE, keep=1))
    msgs = _msgs(5)
    out = comp._truncate(msgs)
    assert out[0] is msgs[0]
    assert out[1]["role"] == "system"
    assert out[2:] == msgs[-1:]


def test_sliding_returns_input_when_short() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.SLIDING, keep=5))
    msgs = _msgs(5)
    assert comp._sliding(msgs) is msgs


def test_sliding_shortens_long_history() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.SLIDING, keep=2))
    msgs = _msgs(6)
    out = comp._sliding(msgs)
    assert out[0] is msgs[0]
    assert out[-2:] == msgs[-2:]


# ── _summarize ──────────────────────────────────────────────────────────


async def test_summarize_returns_input_when_short() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.SUMMARIZE, keep=3))
    msgs = _msgs(4)  # len == keep + 1
    assert await comp._summarize(msgs, FakeModel()) is msgs


async def test_summarize_keeps_leading_system_prompt() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.SUMMARIZE, keep=2))
    msgs = [
        {"role": MessageRole.SYSTEM, "content": "system prompt"},
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
        {"role": "user", "content": "three"},
        {"role": "assistant", "content": "four"},
    ]
    model = FakeModel(content="the recap")
    out = await comp._summarize(msgs, model)
    assert out[0] == {"role": MessageRole.SYSTEM, "content": "system prompt"}
    assert out[1]["content"] == "[Summary of earlier conversation]\nthe recap"
    assert out[-2:] == msgs[-2:]
    # the middle was fed to the model
    prompt = model.calls[0]["messages"][1]["content"]
    assert "[user] one" in prompt
    assert "[assistant] two" in prompt


async def test_summarize_no_leading_system_message() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.SUMMARIZE, keep=2))
    msgs = _msgs(5)  # no system head; all user
    out = await comp._summarize(msgs, FakeModel(content="r"))
    # head is empty -> summary message is first
    assert out[0]["content"] == "[Summary of earlier conversation]\nr"
    assert out[-2:] == msgs[-2:]


async def test_summarize_empty_summary_text_fallback() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.SUMMARIZE, keep=2))
    out = await comp._summarize(_msgs(5), FakeModel(content=None))
    assert out[0]["content"] == "[Summary of earlier conversation]\n[Summary unavailable]"

    out2 = await comp._summarize(_msgs(5), FakeModel(content="   "))
    assert out2[0]["content"] == "[Summary of earlier conversation]\n[Summary unavailable]"


async def test_summarize_model_failure_falls_back_to_truncate() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.SUMMARIZE, keep=2))
    out = await comp._summarize(_msgs(6), FakeModel(exc=RuntimeError("model down")))
    assert out[1]["content"] == "[Earlier conversation truncated for brevity]"


async def test_summarize_returns_input_at_guard_boundary() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.SUMMARIZE, keep=3))
    # len == keep + 1 -> early return before any model call
    msgs = [
        {"role": MessageRole.SYSTEM, "content": "sys"},
        {"role": "user", "content": "1"},
        {"role": "assistant", "content": "2"},
        {"role": "user", "content": "3"},
    ]
    assert await comp._summarize(msgs, FakeModel()) is msgs


async def test_summarize_sync_meter_receives_result() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.SUMMARIZE, keep=2))
    seen: list[Any] = []

    def meter(result: Any) -> None:
        seen.append(result)

    out = await comp._summarize(_msgs(5), FakeModel(content="s"), meter=meter)
    assert out[0]["content"].endswith("s")
    assert len(seen) == 1


async def test_summarize_async_meter_awaited() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.SUMMARIZE, keep=2))
    seen: list[Any] = []

    async def meter(result: Any) -> None:
        seen.append(result)

    await comp._summarize(_msgs(5), FakeModel(content="s"), meter=meter)
    assert len(seen) == 1


async def test_summarize_meter_failure_is_swallowed() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.SUMMARIZE, keep=2))

    def meter(result: Any) -> None:
        raise RuntimeError("meter broke")

    out = await comp._summarize(_msgs(5), FakeModel(content="s"), meter=meter)
    assert out[0]["content"].endswith("s")


# ── compress_with_budget ────────────────────────────────────────────────


def test_compress_with_budget_within_budget_returns_input() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.TRUNCATE))
    msgs = _msgs(2)
    assert comp.compress_with_budget(msgs, max_tokens=10_000) is msgs


def test_compress_with_budget_summarizes_history() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.TRUNCATE))
    msgs = [
        {"role": "system", "content": "s" * 400},  # 100 tokens
        *[{"role": "user", "content": "u" * 400} for _ in range(6)],  # 100 tokens each
    ]
    out = comp.compress_with_budget(msgs, max_tokens=250)
    # system kept, older user messages summarized, at least one kept verbatim
    assert out[0]["role"] == "system"
    assert any(
        isinstance(m.get("content"), str) and m["content"].startswith("<summary of") for m in out
    )


def test_compress_with_budget_all_system_over_budget() -> None:
    comp = ContextCompressor(_config(CompressionStrategy.TRUNCATE))
    msgs = [
        {"role": "system", "content": "a" * 400},
        {"role": "system", "content": "b" * 400},
    ]
    out = comp.compress_with_budget(msgs, max_tokens=10)
    # no non-system messages -> no summary inserted, everything kept
    assert out == msgs
