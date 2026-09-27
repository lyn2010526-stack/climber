"""Focused contracts for model adapter transport and response boundaries."""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

import pytest


class _Response:
    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.status_code = 200
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _AsyncClient:
    instances: ClassVar[list[_AsyncClient]] = []
    response_payload: ClassVar[dict[str, Any]] = {}

    def __init__(self, *, timeout: object) -> None:
        self.timeout = timeout
        self.__class__.instances.append(self)

    async def __aenter__(self) -> _AsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, *args: Any, **kwargs: Any) -> _Response:
        return _Response({})

    async def post(self, *args: Any, **kwargs: Any) -> _Response:
        return _Response(self.response_payload)


@pytest.mark.asyncio
async def test_anthropic_passes_explicit_timeout_to_stream_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.models.anthropic_adapter import AnthropicAdapter

    calls: list[dict[str, Any]] = []

    class _StreamResponse:
        async def __aenter__(self) -> _StreamResponse:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        async def aiter_lines(self):
            if False:
                yield ""

    class _Client:
        def stream(self, *args: Any, **kwargs: Any) -> _StreamResponse:
            calls.append(kwargs)
            return _StreamResponse()

    monkeypatch.setattr(AnthropicAdapter, "get_client", classmethod(lambda cls: _Client()))
    adapter = AnthropicAdapter("claude", "key")
    result = [chunk async for chunk in adapter.stream_chat([], timeout=7)]

    assert result == []
    assert calls[-1]["timeout"] == 7


@pytest.mark.asyncio
async def test_anthropic_cancellation_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.models.anthropic_adapter import AnthropicAdapter

    class _Client:
        def stream(self, *args: Any, **kwargs: Any):
            raise asyncio.CancelledError

    monkeypatch.setattr(AnthropicAdapter, "get_client", classmethod(lambda cls: _Client()))

    with pytest.raises(asyncio.CancelledError):
        await anext(AnthropicAdapter("claude", "key").stream_chat([]))


@pytest.mark.asyncio
async def test_openai_passes_explicit_timeout_to_stream_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.models.openai_adapter import OpenAIAdapter

    calls: list[dict[str, Any]] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        async def aiter_bytes(self):
            yield b'data: [DONE]\n\n'

        async def aclose(self) -> None:
            return None

    class _Client:
        async def send(self, request, **kwargs):
            calls.append(kwargs)
            return _Response()

    monkeypatch.setattr(OpenAIAdapter, "get_client", classmethod(lambda cls: _Client()))
    chunks = [
        chunk
        async for chunk in OpenAIAdapter("gpt", "key").stream_chat(
            [], timeout=11, idle_timeout=1
        )
    ]

    assert chunks[-1].finish_reason == "stop"
    assert calls[-1]["timeout"] == 11


@pytest.mark.asyncio
async def test_ollama_uses_request_timeout_and_decodes_tool_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.models import ollama_adapter
    from app.models.ollama_adapter import OllamaAdapter

    _AsyncClient.instances.clear()
    _AsyncClient.response_payload = {
        "message": {
            "content": "ok",
            "tool_calls": [{
                "function": {"name": "lookup", "arguments": '{"q":"x"}'},
            }],
        },
        "done": True,
    }
    monkeypatch.setattr(ollama_adapter.httpx, "AsyncClient", _AsyncClient)
    monkeypatch.setattr(OllamaAdapter, "_is_ollama_reachable", lambda self, timeout: _async_true())

    async def _request(self, payload, stream=False, timeout=120):
        assert timeout == 9
        return _AsyncClient.response_payload

    monkeypatch.setattr(OllamaAdapter, "_make_request", _request)
    result = await OllamaAdapter("llama", "", "http://ollama").chat([], timeout=9)

    assert result.tool_calls[0]["function"]["arguments"] == {"q": "x"}


async def _async_true() -> bool:
    return True


@pytest.mark.asyncio
async def test_ollama_cancellation_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.models.ollama_adapter import OllamaAdapter

    async def _cancel(self, timeout=2):
        raise asyncio.CancelledError

    monkeypatch.setattr(OllamaAdapter, "_is_ollama_reachable", _cancel)

    with pytest.raises(asyncio.CancelledError):
        await OllamaAdapter("llama", "").chat([])


@pytest.mark.asyncio
async def test_google_http_errors_remain_provider_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    from app.models import google_adapter
    from app.models.google_adapter import GoogleGeminiAdapter

    class _Client:
        def __init__(self, **kwargs: Any) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, *args: Any, **kwargs: Any):
            request = httpx.Request("POST", "https://example.test")
            response = httpx.Response(503, request=request)
            raise httpx.HTTPStatusError("upstream", request=request, response=response)

    monkeypatch.setattr(google_adapter.httpx, "AsyncClient", _Client)

    with pytest.raises(httpx.HTTPStatusError):
        await GoogleGeminiAdapter("gemini", "key").chat([])
