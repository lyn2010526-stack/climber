"""Versioned OpenAI-compatible response contract tests.

DeepSeek exposes reasoning_content and detailed usage alongside standard
OpenAI-compatible tool calls. These tests verify both streaming and
non-streaming paths preserve the fields for downstream consumers.
"""

from __future__ import annotations

import json

import pytest

from app.models.openai_adapter import OpenAIAdapter


class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload

    async def aclose(self) -> None:
        return None


class _Client:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    async def post(self, *args, **kwargs):
        return _Response(self.payload)


class _StreamResponse:
    def __init__(self, lines: list[bytes]) -> None:
        self.lines = lines

    async def aiter_bytes(self):
        for line in self.lines:
            yield line

    async def aclose(self) -> None:
        return None

    def raise_for_status(self) -> None:
        return None


class _StreamClient:
    def __init__(self, response: _StreamResponse) -> None:
        self.response = response

    async def send(self, request, **kwargs):
        return self.response


def _sse(payload: dict) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode()


@pytest.mark.asyncio
async def test_non_stream_preserves_reasoning_usage_and_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "id": "resp-1",
        "model": "deepseek-reasoner",
        "object": "chat.completion",
        "system_fingerprint": "fp-1",
        "choices": [{
            "finish_reason": "stop",
            "message": {
                "role": "assistant",
                "content": "answer",
                "reasoning_content": "private chain",
                "tool_calls": [],
            },
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "prompt_cache_hit_tokens": 4,
            "prompt_cache_miss_tokens": 6,
            "completion_tokens_details": {"reasoning_tokens": 12},
        },
    }
    monkeypatch.setattr(OpenAIAdapter, "get_client", classmethod(lambda cls: _Client(payload)))

    result = await OpenAIAdapter("deepseek-reasoner", "key")._chat_non_streaming([], None)

    assert result.protocol_version == "openai.chat.completions.v1"
    assert result.reasoning_content == "private chain"
    assert result.usage["prompt_cache_hit_tokens"] == 4
    assert result.usage["completion_tokens_details"]["reasoning_tokens"] == 12
    assert result.response_metadata == {
        "id": "resp-1",
        "model": "deepseek-reasoner",
        "system_fingerprint": "fp-1",
        "object": "chat.completion",
    }


@pytest.mark.asyncio
async def test_stream_preserves_reasoning_tool_calls_usage_and_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = [
        _sse({
            "id": "resp-2",
            "model": "deepseek-reasoner",
            "object": "chat.completion.chunk",
            "choices": [{"delta": {"reasoning_content": "think "}}],
        }),
        _sse({
            "choices": [{"delta": {"content": "done", "tool_calls": [{
                "index": 0,
                "id": "call-1",
                "type": "function",
                "function": {"name": "read_file", "arguments": '{"path":"a"}'},
            }]}}],
        }),
        _sse({
            "choices": [{"delta": {}, "finish_reason": "tool_calls"}],
            "usage": {"total_tokens": 17, "prompt_cache_hit_tokens": 3},
        }),
        b"data: [DONE]\n\n",
    ]
    monkeypatch.setattr(
        OpenAIAdapter,
        "get_client",
        classmethod(lambda cls: _StreamClient(_StreamResponse(lines))),
    )

    chunks = [chunk async for chunk in OpenAIAdapter("deepseek-reasoner", "key").stream_chat([])]
    result = await OpenAIAdapter("deepseek-reasoner", "key").chat([])

    assert "think " in "".join(chunk.reasoning_content for chunk in chunks)
    assert chunks[-1].usage["prompt_cache_hit_tokens"] == 3
    assert chunks[-1].response_metadata["id"] == "resp-2"
    assert result.reasoning_content == "think "
    assert result.content == "done"
    assert result.tool_calls[0]["function"]["name"] == "read_file"
    assert result.usage["total_tokens"] == 17
