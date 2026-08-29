"""Regression tests for model adapter streaming lifecycle and aggregation."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest

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
