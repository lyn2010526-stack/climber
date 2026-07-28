"""Tests for ContextCompressor including SUMMARIZE strategy."""

import os

os.environ.setdefault("APP_TESTING", "true")

import pytest

from app.core import CompressionStrategy, ContextConfig, MessageRole
from app.core.compressor import ContextCompressor, estimate_tokens


@pytest.fixture
def fake_adapter():
    class FakeAdapter:
        async def chat(self, messages, tools=None):
            # Build deterministic summary from messages length
            return type("R", (), {
                "content": f"[summary of {len(messages)} msgs]",
                "tool_calls": [],
                "finish_reason": "stop",
                "tokens_used": 1,
            })()

    return FakeAdapter()


def _build_messages(n: int, content: str = "hello world ") -> list[dict]:
    msgs = [{"role": MessageRole.SYSTEM, "content": "system prompt"}]
    for i in range(n):
        msgs.append({"role": "user", "content": f"{content} {i}"})
        msgs.append({"role": "assistant", "content": f"answer {i}"})
    return msgs


def test_truncate_keeps_first_and_recent():
    cfg = ContextConfig(
        max_tokens=10,
        compression_strategy=CompressionStrategy.TRUNCATE,
        keep_recent_messages=3,
    )
    comp = ContextCompressor(cfg)
    msgs = _build_messages(8)
    result = comp._truncate(msgs)
    assert result[0]["content"] == "system prompt"
    assert "truncated" in result[1]["content"].lower()
    assert len(result) == 1 + 1 + 3


def test_sliding_drops_old_msgs():
    cfg = ContextConfig(
        max_tokens=10,
        compression_strategy=CompressionStrategy.SLIDING,
        keep_recent_messages=5,
    )
    comp = ContextCompressor(cfg)
    msgs = _build_messages(10)
    result = comp._sliding(msgs)
    assert len(result) == 5
    assert result[-1]["role"] == "assistant"


def test_needs_compression_respects_budget():
    cfg = ContextConfig(max_tokens=100)
    comp = ContextCompressor(cfg)
    assert comp.needs_compression([{"content": "a" * 10}]) is False
    assert comp.needs_compression([{"content": "a" * 1000}]) is True


@pytest.mark.asyncio
async def test_summarize_uses_adapter(fake_adapter):
    cfg = ContextConfig(
        max_tokens=10,
        compression_strategy=CompressionStrategy.SUMMARIZE,
        keep_recent_messages=3,
    )
    comp = ContextCompressor(cfg)
    msgs = _build_messages(8)
    result = await comp._summarize(msgs, fake_adapter)
    # First system prompt preserved, then summary system message, then last keep=3
    assert result[0]["content"] == "system prompt"
    assert any("[Summary of earlier conversation]" in m.get("content", "") for m in result)
    assert len(result) == 1 + 1 + 3


@pytest.mark.asyncio
async def test_summarize_fallback_on_adapter_error():
    cfg = ContextConfig(
        max_tokens=10,
        compression_strategy=CompressionStrategy.SUMMARIZE,
        keep_recent_messages=3,
    )
    comp = ContextCompressor(cfg)
    msgs = _build_messages(8)

    class BoomAdapter:
        async def chat(self, messages, tools=None):
            raise RuntimeError("boom")

    result = await comp._summarize(msgs, BoomAdapter())
    # Should fall back to truncate (which includes a "truncated" marker)
    assert any("truncated" in m.get("content", "").lower() for m in result)


@pytest.mark.asyncio
async def test_compress_dispatches_by_strategy(fake_adapter):
    cfg_trunc = ContextConfig(
        max_tokens=10,
        compression_strategy=CompressionStrategy.TRUNCATE,
        keep_recent_messages=2,
    )
    comp = ContextCompressor(cfg_trunc)
    msgs = _build_messages(6)
    assert "truncated" in (await comp.compress(msgs, fake_adapter))[1]["content"].lower()

    cfg_sum = ContextConfig(
        max_tokens=10,
        compression_strategy=CompressionStrategy.SUMMARIZE,
        keep_recent_messages=2,
    )
    comp2 = ContextCompressor(cfg_sum)
    out2 = await comp2.compress(msgs, fake_adapter)
    assert "[Summary of earlier conversation]" in out2[1]["content"]


def test_estimate_tokens_handles_tool_calls():
    msgs = [{"content": "abcd", "tool_calls": [{"id": "x" * 40}]}]
    # 1 from content (4 chars) + ~10 from tool_calls (40 chars)
    assert estimate_tokens(msgs) > 0
