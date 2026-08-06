"""Tests for SSE streaming handling.

Validates that the OpenAI adapter's stream_chat properly handles
SSE streaming, including various termination conditions.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio

from app.models.openai_adapter import OpenAIAdapter


class MockResponse:
    """Mock httpx response that yields raw lines for SSE streaming."""

    def __init__(self, sse_frames: list[str], hang_after: bool = False):
        self._frames = sse_frames
        self._hang_after = hang_after
        self.status_code = 200
        self._closed = False

    async def aiter_lines(self) -> AsyncIterator[str]:
        for frame in self._frames:
            if self._closed:
                return
            yield frame
        if self._hang_after:
            try:
                for _ in range(300):
                    if self._closed:
                        return
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                return

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        for frame in self._frames:
            if self._closed:
                return
            yield (frame + "\n").encode()
        if self._hang_after:
            try:
                for _ in range(300):
                    if self._closed:
                        return
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                return

    def raise_for_status(self):
        pass

    async def aclose(self):
        self._closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class MockClient:
    """Mock httpx.AsyncClient that returns a mock streaming response."""

    def __init__(self, response: MockResponse):
        self._response = response

    @asynccontextmanager
    async def stream(self, method, url, headers=None, content=None, timeout=None):
        yield self._response

    async def send(self, request, stream=False):
        return self._response

    async def aclose(self):
        pass


def _build_sse_frames(
    content_chunks: list[str],
    include_done: bool = True,
    finish_reason: str | None = None,
) -> list[str]:
    """Build SSE frame strings for testing."""
    frames: list[str] = []
    for chunk in content_chunks:
        payload = {
            "choices": [{"delta": {"content": chunk}, "finish_reason": None}],
        }
        frames.append(f"data: {json.dumps(payload)}")

    if finish_reason:
        payload = {
            "choices": [{"delta": {}, "finish_reason": finish_reason}],
        }
        frames.append(f"data: {json.dumps(payload)}")

    if include_done:
        frames.append("data: [DONE]")

    return frames


@pytest_asyncio.fixture
def adapter():
    """Create an OpenAIAdapter with mocked client."""
    adapter = OpenAIAdapter(
        model_id="test-model",
        api_key="fake-key",
        base_url="https://fake-api.example.com/v1",
    )
    return adapter


@asynccontextmanager
async def _mock_stream(adapter: OpenAIAdapter, frames: list[str], hang_after: bool = False):
    """Context manager that patches the adapter's client for SSE testing."""
    response = MockResponse(frames, hang_after=hang_after)
    client = MockClient(response)
    original = OpenAIAdapter.get_client
    OpenAIAdapter.get_client = classmethod(lambda cls: client).__get__(OpenAIAdapter)
    try:
        yield
    finally:
        OpenAIAdapter.get_client = original


@pytest.mark.asyncio
async def test_standard_done_terminator(adapter):
    """Standard 'data: [DONE]' should terminate the stream."""
    frames = _build_sse_frames(["Hello", " world"], include_done=True)
    async with _mock_stream(adapter, frames):
        results = []
        async for chunk in adapter.stream_chat(messages=[{"role": "user", "content": "hi"}], timeout=5):
            results.append(chunk)

    assert len(results) > 0
    assert "Hello" in results[-1].content


@pytest.mark.asyncio
async def test_finish_reason_terminator(adapter):
    """finish_reason in choices should be captured."""
    frames = _build_sse_frames(["Data"], include_done=True, finish_reason="stop")
    async with _mock_stream(adapter, frames):
        results = []
        async for chunk in adapter.stream_chat(messages=[{"role": "user", "content": "hi"}], timeout=5):
            results.append(chunk)

    assert len(results) > 0
    assert results[-1].finish_reason == "stop"
    assert "Data" in results[-1].content


@pytest.mark.asyncio
async def test_content_accumulation(adapter):
    """Content from multiple chunks should be accumulated."""
    frames = _build_sse_frames(["Hel", "lo ", "World"], include_done=True)
    async with _mock_stream(adapter, frames):
        last_chunk = None
        async for chunk in adapter.stream_chat(messages=[{"role": "user", "content": "hi"}], timeout=5):
            last_chunk = chunk

    assert last_chunk is not None
    assert "Hello World" in last_chunk.content


@pytest.mark.asyncio
async def test_tool_calls_in_stream(adapter):
    """Tool calls in streaming chunks should be parsed correctly."""
    tool_call_payload = {
        "choices": [{
            "delta": {
                "tool_calls": [{
                    "index": 0,
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "echo", "arguments": json.dumps({"text": "hello"})},
                }]
            }
        }]
    }
    finish_payload = {
        "choices": [{"delta": {}, "finish_reason": "tool_calls"}],
    }
    frames = [
        f"data: {json.dumps(tool_call_payload)}",
        f"data: {json.dumps(finish_payload)}",
    ]
    async with _mock_stream(adapter, frames):
        results = []
        async for chunk in adapter.stream_chat(messages=[{"role": "user", "content": "echo hi"}], timeout=5):
            results.append(chunk)

    assert len(results) > 0
    assert results[-1].finish_reason == "tool_calls"
    assert len(results[-1].tool_calls) > 0
    assert results[-1].tool_calls[0]["function"]["name"] == "echo"


@pytest.mark.asyncio
async def test_empty_lines_and_comments_ignored(adapter):
    """Empty lines and SSE comments should be skipped."""
    frames = [
        ": keep-alive",
        "",
        'data: {"choices": [{"delta": {"content": "Hi"}}]}',
        "data: [DONE]",
    ]
    async with _mock_stream(adapter, frames):
        results = []
        async for chunk in adapter.stream_chat(messages=[{"role": "user", "content": "hi"}], timeout=5):
            results.append(chunk)

    assert len(results) > 0
    assert results[-1].content == "Hi"


@pytest.mark.asyncio
async def test_tokens_extracted_from_usage(adapter):
    """Token counts should be extracted from usage fields."""
    frames = [
        'data: {"choices": [{"delta": {"content": "Hi"}}], "usage": {"total_tokens": 42}}',
        "data: [DONE]",
    ]
    async with _mock_stream(adapter, frames):
        results = []
        async for chunk in adapter.stream_chat(messages=[{"role": "user", "content": "hi"}], timeout=5):
            results.append(chunk)

    assert len(results) > 0
    assert results[-1].tokens_used == 42


@pytest.mark.asyncio
async def test_no_frames_yields_no_results(adapter):
    """Stream with only [DONE] should yield nothing."""
    frames = ["data: [DONE]"]
    async with _mock_stream(adapter, frames):
        results = []
        async for chunk in adapter.stream_chat(messages=[{"role": "user", "content": "hi"}], timeout=5):
            results.append(chunk)

    assert len(results) == 0
