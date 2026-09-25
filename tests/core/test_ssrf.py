"""SSRF protection tests for outbound HTTP tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.utils.ssrf import blocked_reason


def _fake_getaddrinfo(public_ip: str):
    def _getaddrinfo(host, port, *args, **kwargs):
        import socket
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (public_ip, port or 80))]
    return _getaddrinfo


@pytest.mark.parametrize("url", [
    "http://169.254.169.254/latest/meta-data/",
    "http://127.0.0.1/",
    "http://localhost:8000/admin",
    "http://10.0.0.5/",
    "http://192.168.1.1/",
    "http://[::1]/",
    "http://metadata.google.internal/",
    "file:///etc/passwd",
    "ftp://example.com/file",
])
def test_blocked_reason_rejects_unsafe_urls(url):
    assert blocked_reason(url) is not None


@pytest.mark.parametrize("url", [
    "https://example.com/",
    "https://www.wikipedia.org/",
    "https://api.github.com/",
])
def test_blocked_reason_allows_public_urls(url):
    with patch("app.utils.ssrf.socket.getaddrinfo", _fake_getaddrinfo("8.8.8.8")):
        assert blocked_reason(url) is None


def test_blocked_reason_rejects_private_resolved_host():
    with patch("app.utils.ssrf.socket.getaddrinfo", _fake_getaddrinfo("127.0.0.1")):
        assert blocked_reason("http://attacker.example/") is not None


def test_download_file_blocks_private_url():
    from app.tools import native_tools

    with patch(
        "app.utils.ssrf.blocked_reason",
        return_value="Address '10.0.0.5' is not reachable externally",
    ):
        result = awaitable_result(native_tools.download_file("http://10.0.0.5/evil.bin", "/tmp/evil.bin"))
    assert "blocked" in result
    assert "not reachable externally" in result


def test_download_file_blocks_redirect_to_private():
    from unittest.mock import Mock

    from app.tools import native_tools

    def fake_blocked_reason(url):
        return "Address '10.0.0.5' is not reachable externally" if "10.0.0.5" in url else None

    fake_redirect = Mock()
    fake_redirect.is_redirect = True
    fake_redirect.headers = {"location": "http://10.0.0.5/steal"}
    fake_ok = Mock()
    fake_ok.is_redirect = False
    fake_ok.content = b"data"

    calls = {"n": 0}

    async def fake_get(url):
        calls["n"] += 1
        return fake_redirect if calls["n"] == 1 else fake_ok

    fake_client = Mock()
    fake_client.get = fake_get
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=fake_client), \
         patch("app.utils.ssrf.blocked_reason", fake_blocked_reason):
        result = awaitable_result(
            native_tools.download_file(
                "http://example.com/redirect", "/tmp/out.bin"
            )
        )
    assert "blocked redirect" in result
    assert calls["n"] == 1


def awaitable_result(coro):
    import asyncio
    return asyncio.run(coro)


def test_fetch_url_checks_blocked_reason_first(monkeypatch):
    from app.tools import builtins

    called = []
    fake_fetch = AsyncMock(side_effect=lambda url: called.append(url))

    monkeypatch.setattr(builtins, "blocked_reason", lambda url: "Address '169.254.169.254' is blocked")
    monkeypatch.setattr(builtins, "httpx", AsyncMock())
    builtins.httpx.AsyncClient.return_value = AsyncMock()
    builtins.httpx.AsyncClient.return_value.get = fake_fetch
    import asyncio

    result = asyncio.run(builtins.fetch_url("http://169.254.169.254/"))
    assert "blocked" in result
    assert called == []