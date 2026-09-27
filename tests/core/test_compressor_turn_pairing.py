"""Compression turn-pairing preservation tests (research-100 P0).

Verifies that TRUNCATE/SLIDING compression does not split an assistant
message carrying tool_calls from its immediately following TOOL result
messages, matching the linear-history integrity observed in mini-swe-agent
and OpenCode's Auto-Compact design.
"""

from __future__ import annotations

from app.core import CompressionStrategy, ContextConfig
from app.core.compressor import ContextCompressor


def _turn(iteration: int) -> list[dict]:
    return [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": f"tool_{iteration}", "arguments": {}}}],
        },
        {"role": "tool", "content": f"result_{iteration}", "tool_call_id": f"call_{iteration}"},
    ]


def _history(turns: int) -> list[dict]:
    messages = [{"role": "system", "content": "system"}]
    for i in range(1, turns + 1):
        messages.extend(_turn(i))
    return messages


def test_truncate_keeps_assistant_tool_pair_when_partial() -> None:
    cfg = ContextConfig(max_tokens=4096, compression_strategy=CompressionStrategy.TRUNCATE, keep_recent_messages=3)
    messages = _history(5)  # system + 5 turns = 11 messages
    compressed = ContextCompressor(cfg)._truncate(messages)
    # system + marker + recent complete turns
    tail = compressed[2:]
    # the kept tool result must never appear without its assistant tool_calls
    roles = [m["role"] for m in tail]
    assert roles.count("tool") == roles.count("assistant")
    # most recent turn intact
    assert tail[-2]["role"] == "assistant"
    assert tail[-1] == {"role": "tool", "content": "result_5", "tool_call_id": "call_5"}


def test_sliding_keeps_assistant_tool_pair_when_partial() -> None:
    cfg = ContextConfig(max_tokens=4096, compression_strategy=CompressionStrategy.SLIDING, keep_recent_messages=2)
    messages = _history(4)
    compressed = ContextCompressor(cfg)._sliding(messages)
    tail = compressed[2:]
    roles = [m["role"] for m in tail]
    assert roles.count("tool") == roles.count("assistant")
    assert tail[0] == {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "tool_3", "arguments": {}}}],
    }


def test_truncate_when_tail_is_tool_extends_to_assistant() -> None:
    # Regression: when keep_recent_messages lands on a TOOL message boundary,
    # the algorithm must extend back to include its assistant tool_calls.
    cfg = ContextConfig(max_tokens=4096, compression_strategy=CompressionStrategy.TRUNCATE, keep_recent_messages=4)
    messages = _history(4)  # 1 + 8 = 9 messages; keep 4 lands mid-pair
    compressed = ContextCompressor(cfg)._truncate(messages)
    tail = compressed[2:]
    roles = [m["role"] for m in tail]
    assert roles[0] == "assistant"
    assert roles[1] == "tool"
    assert roles.count("tool") == roles.count("assistant")


def test_compress_dispatches_and_preserves_pairing() -> None:
    import asyncio

    cfg = ContextConfig(max_tokens=4096, compression_strategy=CompressionStrategy.TRUNCATE, keep_recent_messages=2)
    messages = _history(6)
    compressed = asyncio.run(ContextCompressor(cfg).compress(messages, model=None))
    tail = compressed[2:]
    roles = [m["role"] for m in tail]
    assert roles.count("tool") == roles.count("assistant")
    assert tail[-1] == {"role": "tool", "content": "result_6", "tool_call_id": "call_6"}


def test_short_history_untouched() -> None:
    cfg = ContextConfig(max_tokens=4096, compression_strategy=CompressionStrategy.TRUNCATE, keep_recent_messages=5)
    messages = _history(2)  # short: no compression
    assert ContextCompressor(cfg)._truncate(messages) == messages


def test_compression_keeps_first_user_message_without_system_prompt() -> None:
    cfg = ContextConfig(max_tokens=4096, compression_strategy=CompressionStrategy.TRUNCATE, keep_recent_messages=2)
    messages = [{"role": "user", "content": "initial request"}]
    messages.extend([{"role": "user", "content": "follow up"}, {"role": "assistant", "content": "answer"}])

    compressed = ContextCompressor(cfg)._truncate(messages)

    assert compressed[0]["role"] == "system"
    assert "initial request" not in str(compressed)
    assert compressed[-2:][0]["content"] == "follow up"


def test_needs_compression_uses_configured_threshold() -> None:
    cfg = ContextConfig(max_tokens=100, summarize_threshold=0.8)
    compressor = ContextCompressor(cfg)
    messages = [{"role": "user", "content": "x" * 320}]

    assert compressor.needs_compression(messages)


def test_summarize_failure_falls_back_without_raising() -> None:
    class FailingModel:
        async def chat(self, **kwargs):
            raise RuntimeError("model unavailable")

    cfg = ContextConfig(compression_strategy=CompressionStrategy.SUMMARIZE, keep_recent_messages=2)
    messages = [{"role": "user", "content": f"message-{i}"} for i in range(5)]

    compressed = __import__("asyncio").run(ContextCompressor(cfg).compress(messages, FailingModel()))

    assert compressed
    assert compressed[-1] == messages[-1]
