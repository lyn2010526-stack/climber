"""Tests for SSRF enforcement on the tool execution path.

``app/utils/ssrf.py`` implemented the address checks but had no production
caller, so metadata endpoints and loopback hosts were reachable. The guard now
lives in ``ToolRegistry.execute()``, which every tool invocation passes through.
"""

from __future__ import annotations

import pytest

from app.tools import ToolRegistry, browser_tools
from app.tools.mcp_client import MCPClient


@pytest.fixture(autouse=True)
def registry_with_stub_tool():
    registry = ToolRegistry()
    calls: list[str] = []

    async def _stub(url: str = "") -> str:
        calls.append(url)
        return f"fetched {url}"

    registry.register("fetch_url", "Fetch a URL", {"type": "object", "properties": {}}, _stub)
    # The egress gate is class-level state; the SSRF guard sits behind it, so
    # these tests need egress open to observe the SSRF decision.
    ToolRegistry.set_network_enabled(True)
    yield registry, calls
    ToolRegistry.set_network_enabled(True)


async def test_blocks_cloud_metadata_endpoint(registry_with_stub_tool):
    registry, calls = registry_with_stub_tool
    result = await registry.execute("fetch_url", {"url": "http://169.254.169.254/latest/meta-data/"})
    assert "SSRF" in result
    assert calls == [], "the network call must not be attempted"


async def test_blocks_loopback_and_private_ranges(registry_with_stub_tool):
    registry, _ = registry_with_stub_tool
    for target in (
        "http://127.0.0.1:8080/admin",
        "http://localhost:5000/",
        "http://10.0.0.5/internal",
        "http://192.168.1.1/router",
    ):
        result = await registry.execute("fetch_url", {"url": target})
        assert "SSRF" in result, f"{target} should be blocked"


async def test_blocks_non_http_schemes(registry_with_stub_tool):
    registry, _ = registry_with_stub_tool
    for target in ("file:///etc/passwd", "gopher://127.0.0.1:11211/_x", "ftp://example.com"):
        result = await registry.execute("fetch_url", {"url": target})
        assert "SSRF" in result, f"{target} should be blocked"


async def test_allows_public_url_and_reaches_the_tool(registry_with_stub_tool):
    registry, calls = registry_with_stub_tool
    result = await registry.execute("fetch_url", {"url": "https://example.com/docs"})
    assert "SSRF" not in result
    assert calls == ["https://example.com/docs"]


async def test_guard_respects_the_egress_gate_precedence(registry_with_stub_tool):
    """A disabled deployment reports the egress gate, not the SSRF reason."""
    registry, _ = registry_with_stub_tool
    ToolRegistry.set_network_enabled(False)
    result = await registry.execute("fetch_url", {"url": "http://169.254.169.254/"})
    assert "network access is disabled" in result


async def test_non_network_tools_skip_the_ssrf_check(registry_with_stub_tool):
    """The guard must not block local tools that happen to take a path string."""
    registry, calls = registry_with_stub_tool

    async def _local(path: str = "") -> str:
        calls.append(path)
        return "local ok"

    registry.register("read_file", "Read a file", {"type": "object", "properties": {}}, _local)
    result = await registry.execute("read_file", {"path": "http://127.0.0.1/secret"})
    assert "SSRF" not in result
    assert calls == ["http://127.0.0.1/secret"]


async def test_url_argument_aliases_are_checked(registry_with_stub_tool):
    registry, calls = registry_with_stub_tool
    for key in ("uri", "target", "link", "endpoint"):
        result = await registry.execute("fetch_url", {key: "http://169.254.169.254/"})
        assert "SSRF" in result, f"alias '{key}' must be inspected"
    assert calls == []


@pytest.mark.asyncio
async def test_browser_navigation_blocks_before_session_creation(monkeypatch):
    async def _unexpected(*args, **kwargs):
        raise AssertionError("blocked URL must not create a browser session")

    monkeypatch.setattr(browser_tools, "_get_or_create_page", _unexpected)

    result = await browser_tools.browser_navigate("http://127.0.0.1:8080/admin")

    assert "SSRF" in result


@pytest.mark.asyncio
async def test_browser_navigation_allows_public_destination_and_dispatches(monkeypatch):
    class _Context:
        _ssrf_route_installed = True
        _ssrf_blocked_reason = None

    class _Page:
        context = _Context()

        async def goto(self, url, **kwargs):
            self.url = url

        async def title(self):
            return "Example"

        async def inner_text(self, selector):
            return "safe body"

    page = _Page()

    async def _get_page(_session_id):
        return page

    monkeypatch.setattr(browser_tools, "_get_or_create_page", _get_page)
    monkeypatch.setattr(browser_tools, "clean_web_content", lambda _url, text: text)

    result = await browser_tools.browser_navigate("https://example.com")

    assert result.startswith("Title: Example")
    assert page.url == "https://example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["http://127.0.0.1/redirect", "http://169.254.169.254/metadata"])
async def test_browser_route_blocks_redirect_and_request_destinations(monkeypatch, url):
    class _Context:
        _ssrf_route_installed = False

        async def route(self, _pattern, handler):
            self.handler = handler

    class _Request:
        def __init__(self, request_url):
            self.url = request_url

    class _Route:
        def __init__(self, request_url):
            self.request = _Request(request_url)
            self.aborted = False
            self.continued = False

        async def abort(self):
            self.aborted = True

        async def continue_(self):
            self.continued = True

    context = _Context()
    await browser_tools._install_ssrf_route(context)
    route = _Route(url)

    await context.handler(route)

    assert route.aborted is True
    assert route.continued is False
    assert "SSRF" in browser_tools._ssrf_error(context)


@pytest.mark.asyncio
async def test_browser_route_allows_initial_request_then_blocks_redirect(monkeypatch):
    class _Context:
        _ssrf_route_installed = False

        async def route(self, _pattern, handler):
            self.handler = handler

    class _Request:
        def __init__(self, request_url):
            self.url = request_url

    class _Route:
        def __init__(self, request_url):
            self.request = _Request(request_url)
            self.aborted = False
            self.continued = False

        async def abort(self):
            self.aborted = True

        async def continue_(self):
            self.continued = True

    context = _Context()
    await browser_tools._install_ssrf_route(context)
    initial = _Route("https://example.com")
    redirect = _Route("http://127.0.0.1/private")

    await context.handler(initial)
    await context.handler(redirect)

    assert initial.continued is True
    assert initial.aborted is False
    assert redirect.aborted is True
    assert redirect.continued is False


@pytest.mark.asyncio
async def test_direct_download_blocks_before_http_client_creation(monkeypatch):
    from app.tools import native_tools

    def _unexpected(*args, **kwargs):
        raise AssertionError("blocked URL must not create an HTTP client")

    monkeypatch.setattr("httpx.AsyncClient", _unexpected)
    result = await native_tools.download_file("http://127.0.0.1/secret", "/tmp/out")
    assert "SSRF" in result


@pytest.mark.asyncio
async def test_open_browser_blocks_before_browser_dispatch(monkeypatch):
    from app.tools import native_tools

    monkeypatch.setattr(
        "webbrowser.open",
        lambda *_args, **_kwargs: pytest.fail("blocked URL must not open a browser"),
    )
    result = await native_tools.open_browser("http://127.0.0.1/admin")
    assert "SSRF" in result


@pytest.mark.asyncio
async def test_mcp_http_endpoint_blocks_before_transport_creation(monkeypatch):
    client = MCPClient("internal", transport="streamable_http", url="http://127.0.0.1:8080/mcp")
    transport_called = False

    def _unexpected(*args, **kwargs):
        nonlocal transport_called
        transport_called = True
        raise AssertionError("blocked URL must not create an MCP transport")

    monkeypatch.setattr("app.tools.mcp_client._MCP_AVAILABLE", True)
    monkeypatch.setattr("app.tools.mcp_client.streamablehttp_client", _unexpected)

    with pytest.raises(ValueError, match="SSRF"):
        await client._connect_http()

    assert transport_called is False


def test_ssrf_rejects_embedded_credentials_and_trailing_dot_private_host(monkeypatch):
    from app.utils import ssrf

    assert "credentials" in ssrf.blocked_reason("https://user:pass@example.com/")
    assert ssrf.blocked_reason("http://127.0.0.1./") is not None


def test_ssrf_rejects_uppercase_scheme():
    from app.utils import ssrf

    assert ssrf.blocked_reason("HTTP://127.0.0.1/") is not None


def test_ssrf_rejects_malformed_host_without_raising():
    from app.utils.ssrf import blocked_reason

    assert blocked_reason("http://[not-an-ip") is not None


def test_research_does_not_follow_unvalidated_redirects(monkeypatch):
    from app.tools import research

    class _Response:
        headers = type("Headers", (), {"get_content_charset": lambda self: "utf-8"})()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, _limit):
            return b"safe body"

    opened: list[str] = []

    def _open(request, timeout):
        opened.append(request.full_url)
        return _Response()

    monkeypatch.setattr(research, "urlopen", _open)
    assert research._fetch_url_sync("https://example.com", 3) == "safe body"
    assert opened == ["https://example.com"]


def test_dns_resolution_failure_fails_closed(monkeypatch):
    import socket

    from app.utils import ssrf

    def _unresolved(*args, **kwargs):
        raise socket.gaierror("temporary DNS failure")

    monkeypatch.setattr(ssrf.socket, "getaddrinfo", _unresolved)

    reason = ssrf.blocked_reason("https://public.example/resource")

    assert reason is not None
    assert "could not be resolved safely" in reason
