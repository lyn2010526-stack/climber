"""Google adapter request timeout contract tests."""

from __future__ import annotations

from typing import ClassVar

import pytest


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "candidates": [
                {
                    "content": {"parts": [{"text": "ok"}]},
                    "finishReason": "STOP",
                }
            ],
        }


class _Client:
    instances: ClassVar[list[_Client]] = []

    def __init__(self, *, timeout: object) -> None:
        self.timeout = timeout
        self.__class__.instances.append(self)

    async def __aenter__(self) -> _Client:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, *args, **kwargs) -> _Response:
        return _Response()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("request_timeout", "expected_timeout"),
    [(None, 60), (7, 7)],
)
async def test_google_chat_uses_default_or_explicit_timeout(
    monkeypatch: pytest.MonkeyPatch,
    request_timeout: int | None,
    expected_timeout: int,
) -> None:
    from app.models import google_adapter
    from app.models.google_adapter import GoogleGeminiAdapter

    _Client.instances.clear()
    monkeypatch.setattr(google_adapter.httpx, "AsyncClient", _Client)
    adapter = GoogleGeminiAdapter("gemini-test", "test-key")

    kwargs = {} if request_timeout is None else {"timeout": request_timeout}
    result = await adapter.chat([{"role": "user", "content": "hello"}], **kwargs)

    assert result.content == "ok"
    assert _Client.instances[-1].timeout == expected_timeout
