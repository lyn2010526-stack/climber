"""Regression tests for model adapter streaming lifecycle and aggregation."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest

from app.models.anthropic_adapter import AnthropicAdapter
from app.models.ollama_adapter import OllamaAdapter
from app.models.openai_adapter import OpenAIAdapter


class _OpenAIResponse:
    status_code = 200

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        for content in ("Hel", "lo"):
            payload = {"choices": [{"delta": {"content": content}}]}
            yield f"data: {json.dumps(payload)}\n".encode()
        yield b"data: [DONE]\n"

    def raise_for_status(self) -> None:
        return None

    async def aclose(self) -> None:
        return None


class _OpenAIClient:
    def __init__(self, response: _OpenAIResponse):
        self.response = response

    async def send(self, request, stream=False):
        return self.response


@pytest.mark.asyncio
async def test_openai_chat_does_not_join_incremental_and_accumulated_content(monkeypatch):
    adapter = OpenAIAdapter("test-model", "test-key", "https://example.test/v1")
    monkeypatch.setattr(
        OpenAIAdapter,
        "get_client",
        classmethod(lambda cls: _OpenAIClient(_OpenAIResponse())),
    )

    result = await adapter.chat([{"role": "user", "content": "hi"}])

    assert result.content == "Hello"
    assert result.accumulated_content == "Hello"


@pytest.mark.asyncio
async def test_openai_stream_emits_only_incremental_content(monkeypatch):
    adapter = OpenAIAdapter("test-model", "test-key", "https://example.test/v1")
    monkeypatch.setattr(
        OpenAIAdapter,
        "get_client",
        classmethod(lambda cls: _OpenAIClient(_OpenAIResponse())),
    )

    chunks = [
        chunk
        async for chunk in adapter.stream_chat([{"role": "user", "content": "hi"}])
    ]

    assert [chunk.content for chunk in chunks] == ["Hel", "lo", ""]
    assert chunks[-1].accumulated_content == "Hello"


class _OpenAICachedUsageResponse(_OpenAIResponse):
    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        content_payload = {
            "choices": [{"delta": {"content": "cached"}}],
        }
        usage_payload = {
            "choices": [],
            "usage": {
                "total_tokens": 11,
                "prompt_tokens_details": {"cached_tokens": 7},
            },
        }
        yield f"data: {json.dumps(content_payload)}\n".encode()
        yield f"data: {json.dumps(usage_payload)}\n".encode()
        yield b"data: [DONE]\n"


class _OpenAITerminalFrameResponse(_OpenAIResponse):
    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        content_payload = {"choices": [{"delta": {"content": "done"}}]}
        terminal_payload = {
            "choices": [{"delta": {}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 13},
        }
        yield f"data: {json.dumps(content_payload)}\n".encode()
        yield f"data: {json.dumps(terminal_payload)}\n".encode()


class _OpenAITerminalFrameWithoutNewlineResponse(_OpenAIResponse):
    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        terminal_payload = {
            "choices": [{"delta": {"content": "done"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 13},
        }
        yield f"data: {json.dumps(terminal_payload)}".encode()


@pytest.mark.asyncio
async def test_openai_cached_token_usage_is_exposed(monkeypatch):
    adapter = OpenAIAdapter("cached-model", "test-key", "https://example.test/v1")
    monkeypatch.setattr(
        OpenAIAdapter,
        "get_client",
        classmethod(lambda cls: _OpenAIClient(_OpenAICachedUsageResponse())),
    )

    result = await adapter.chat([{"role": "user", "content": "hi"}])

    assert result.cached_tokens == 7
    assert result.tokens_used == 11


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response_type",
    [_OpenAITerminalFrameResponse, _OpenAITerminalFrameWithoutNewlineResponse],
)
async def test_openai_terminal_frame_is_emitted_once_with_metadata(monkeypatch, response_type):
    adapter = OpenAIAdapter("test-model", "test-key", "https://example.test/v1")
    monkeypatch.setattr(
        OpenAIAdapter,
        "get_client",
        classmethod(lambda cls: _OpenAIClient(response_type())),
    )

    chunks = [chunk async for chunk in adapter.stream_chat([{"role": "user", "content": "hi"}])]

    assert "".join(chunk.content for chunk in chunks) == "done"
    assert len([chunk for chunk in chunks if chunk.finish_reason == "stop"]) == 1
    assert chunks[-1].tokens_used == 13
    assert chunks[-1].accumulated_content == "done"


class _AnthropicResponse:
    def raise_for_status(self) -> None:
        return None

    async def aiter_lines(self) -> AsyncIterator[str]:
        events = [
            {
                "type": "message_start",
                "message": {
                    "usage": {
                        "input_tokens": 10,
                        "cache_read_input_tokens": 6,
                        "cache_creation_input_tokens": 3,
                    }
                },
            },
            {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "hello"}},
            {"type": "message_delta", "usage": {"output_tokens": 2}},
        ]
        for event in events:
            yield f"data: {json.dumps(event)}"


class _AnthropicStreamContext:
    async def __aenter__(self):
        return _AnthropicResponse()

    async def __aexit__(self, *args):
        return None


class _AnthropicClient:
    def stream(self, *args, **kwargs):
        return _AnthropicStreamContext()


@pytest.mark.asyncio
async def test_anthropic_cached_token_usage_is_exposed(monkeypatch):
    adapter = AnthropicAdapter("cached-model", "test-key")
    monkeypatch.setattr(
        AnthropicAdapter,
        "get_client",
        classmethod(lambda cls: _AnthropicClient()),
    )

    result = await adapter.chat([{"role": "user", "content": "hi"}])

    assert result.cached_tokens == 6
    assert result.cache_creation_tokens == 3
    assert result.tokens_used == 12


class _OllamaResponse:
    def __init__(self):
        self.closed = False

    def raise_for_status(self) -> None:
        return None

    async def aiter_lines(self) -> AsyncIterator[str]:
        if self.closed:
            raise RuntimeError("response was closed before consumption")
        yield json.dumps({"message": {"content": "Hello"}})
        yield json.dumps({"done": True})


class _OllamaStreamContext:
    def __init__(self, response: _OllamaResponse):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, *args):
        self.response.closed = True


class _OllamaClient:
    def __init__(self, response: _OllamaResponse):
        self.response = response

    def stream(self, method, url, json):
        return _OllamaStreamContext(self.response)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None


@pytest.mark.asyncio
async def test_ollama_stream_consumes_response_before_context_exit(monkeypatch):
    response = _OllamaResponse()
    monkeypatch.setattr(
        "app.models.ollama_adapter.httpx.AsyncClient",
        lambda timeout: _OllamaClient(response),
    )
    adapter = OllamaAdapter("test-model", "", "http://ollama.test")
    monkeypatch.setattr(adapter, "_is_ollama_reachable", lambda: _async_true())

    results = [chunk async for chunk in adapter.stream_chat([])]

    assert [result.content for result in results] == ["Hello", ""]


async def _async_true() -> bool:
    return True
