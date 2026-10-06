"""Coverage tests for app.tools.mcp_client (fakes, no real MCP transport)."""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest

from app.tools import mcp_client
from app.tools.mcp_client import MCPClient, MCPRegistry
from app.tools.mcp_models import MCPTool

# ─── fakes ──────────────────────────────────────────────────────────────────


class FakeTransportCM:
    def __init__(self, enter_value):
        self._enter_value = enter_value
        self.entered = 0
        self.exited = 0

    async def __aenter__(self):
        self.entered += 1
        return self._enter_value

    async def __aexit__(self, *exc):
        self.exited += 1
        return False


class FakeSession:
    def __init__(
        self,
        init_result=None,
        *,
        list_tools_page=None,
        list_tools_error=None,
        list_resources_result=None,
        list_resources_error=None,
        list_prompts_result=None,
        list_prompts_error=None,
        read_resource_result=None,
        get_prompt_result=None,
        call_tool_result=None,
        call_tool_error=None,
        close_error=None,
    ):
        self.init_result = init_result
        self._list_tools_page = list_tools_page
        self.list_tools_error = list_tools_error
        self.list_resources_result = list_resources_result
        self.list_resources_error = list_resources_error
        self.list_prompts_result = list_prompts_result
        self.list_prompts_error = list_prompts_error
        self.read_resource_result = read_resource_result
        self.get_prompt_result = get_prompt_result
        self.call_tool_result = call_tool_result
        self.call_tool_error = call_tool_error
        self.close_error = close_error
        self.enter_count = 0
        self.exit_count = 0
        self.list_tools_calls = []
        self.tool_calls = []

    async def __aenter__(self):
        self.enter_count += 1
        return self

    async def __aexit__(self, *exc):
        self.exit_count += 1
        if self.close_error:
            raise self.close_error
        return False

    async def initialize(self):
        return self.init_result

    async def list_tools(self, **kwargs):
        self.list_tools_calls.append(kwargs)
        if self.list_tools_error:
            raise self.list_tools_error
        return self._list_tools_page

    async def call_tool(self, name, arguments):
        self.tool_calls.append((name, arguments))
        if self.call_tool_error:
            raise self.call_tool_error
        return self.call_tool_result

    async def list_resources(self):
        if self.list_resources_error:
            raise self.list_resources_error
        return self.list_resources_result

    async def read_resource(self, uri):
        return self.read_resource_result

    async def list_prompts(self):
        if self.list_prompts_error:
            raise self.list_prompts_error
        return self.list_prompts_result

    async def get_prompt(self, **kwargs):
        return self.get_prompt_result


def _raw_tool(name="search", **extra):
    fields = {
        "name": name,
        "description": "desc",
        "inputSchema": {"type": "object"},
    }
    fields.update(extra)
    return SimpleNamespace(**fields)


def _init_result(capabilities=None):
    caps = capabilities if capabilities is not None else SimpleNamespace(model_dump=lambda: {})
    return SimpleNamespace(
        serverInfo=SimpleNamespace(name="srv", version="1.0"),
        protocolVersion="2024-11-05",
        capabilities=caps,
    )


def _install_mcp_stub(monkeypatch, *, stdio_params=None, sse_client=None):
    """Install minimal fake `mcp.client.stdio` / `mcp.client.sse` modules."""
    mcp_pkg = types.ModuleType("mcp")
    client_pkg = types.ModuleType("mcp.client")
    stdio_mod = types.ModuleType("mcp.client.stdio")
    sse_mod = types.ModuleType("mcp.client.sse")
    stdio_mod.StdioServerParameters = (
        stdio_params if stdio_params is not None else (lambda **kw: kw)
    )
    sse_mod.sse_client = sse_client if sse_client is not None else (lambda **kw: kw)
    monkeypatch.setitem(sys.modules, "mcp", mcp_pkg)
    monkeypatch.setitem(sys.modules, "mcp.client", client_pkg)
    monkeypatch.setitem(sys.modules, "mcp.client.stdio", stdio_mod)
    monkeypatch.setitem(sys.modules, "mcp.client.sse", sse_mod)


# ─── construction / properties ──────────────────────────────────────────────


def test_client_constructor_defaults():
    client = MCPClient(name="a")
    assert client.name == "a"
    assert client.transport == "stdio"
    assert client.command is None
    assert client.args == []
    assert client.url is None
    assert client.headers == {}
    assert client.env == {}
    assert client.session is None
    assert client.tools == {}
    assert client.resources == {}
    assert client.prompts == {}
    assert client.is_connected is False


def test_client_constructor_full():
    client = MCPClient(
        name="b",
        transport="streamable_http",
        command="cmd",
        args=["a", "b"],
        url="http://u",
        headers={"h": "1"},
        env={"E": "1"},
    )
    assert client.args == ["a", "b"]
    assert client.headers == {"h": "1"}
    assert client.env == {"E": "1"}


def test_is_connected_true_with_session():
    client = MCPClient(name="x")
    client.session = FakeSession()
    assert client.is_connected is True


# ─── connect dispatch ───────────────────────────────────────────────────────


async def test_connect_raises_when_mcp_unavailable(monkeypatch):
    monkeypatch.setattr(mcp_client, "_MCP_AVAILABLE", False)
    client = MCPClient(name="x")
    with pytest.raises(ImportError):
        await client.connect()


async def test_connect_unsupported_transport(monkeypatch):
    monkeypatch.setattr(mcp_client, "_MCP_AVAILABLE", True)
    client = MCPClient(name="x", transport="nope")
    with pytest.raises(ValueError, match="Unsupported transport"):
        await client.connect()


async def test_connect_dispatch_each_transport(monkeypatch):
    monkeypatch.setattr(mcp_client, "_MCP_AVAILABLE", True)
    calls = []

    for transport, method in (
        ("stdio", "_connect_stdio"),
        ("streamable_http", "_connect_http"),
        ("sse", "_connect_sse"),
    ):
        client = MCPClient(name="x", transport=transport)

        async def _recorder(_self, _m=method):
            calls.append(_m)

        monkeypatch.setattr(mcp_client.MCPClient, method, _recorder)
        await client.connect()
    assert calls == ["_connect_stdio", "_connect_http", "_connect_sse"]


# ─── transport connect methods ──────────────────────────────────────────────


async def test_connect_stdio_raises_when_mcp_unavailable(monkeypatch):
    monkeypatch.setattr(mcp_client, "_MCP_AVAILABLE", False)
    client = MCPClient(name="x", transport="stdio", command="cmd")
    with pytest.raises(ImportError):
        await client._connect_stdio()


async def test_connect_stdio_requires_command(monkeypatch):
    monkeypatch.setattr(mcp_client, "_MCP_AVAILABLE", True)
    _install_mcp_stub(monkeypatch)
    client = MCPClient(name="x", transport="stdio")
    with pytest.raises(ValueError, match="requires 'command'"):
        await client._connect_stdio()


async def test_connect_stdio_success(monkeypatch):
    monkeypatch.setattr(mcp_client, "_MCP_AVAILABLE", True)
    captured = {}

    def _stdio_client(params):
        captured["params"] = params
        return FakeTransportCM(("read", "write"))

    monkeypatch.setattr(mcp_client, "stdio_client", _stdio_client)
    session = FakeSession(_init_result())
    monkeypatch.setattr(mcp_client, "ClientSession", lambda r, w: session)
    _install_mcp_stub(monkeypatch, stdio_params=lambda **kw: SimpleNamespace(**kw))

    client = MCPClient(name="x", transport="stdio", command="cmd", args=["-y"], env={"E": "1"})
    await client._connect_stdio()

    assert captured["params"].command == "cmd"
    assert captured["params"].args == ["-y"]
    assert client.session is session
    assert session.enter_count == 1
    assert client._server_info["name"] == "srv"


async def test_connect_http_raises_when_mcp_unavailable(monkeypatch):
    monkeypatch.setattr(mcp_client, "_MCP_AVAILABLE", False)
    client = MCPClient(name="x", transport="streamable_http", url="http://u")
    with pytest.raises(ImportError):
        await client._connect_http()


async def test_connect_http_requires_url(monkeypatch):
    monkeypatch.setattr(mcp_client, "_MCP_AVAILABLE", True)
    client = MCPClient(name="x", transport="streamable_http")
    with pytest.raises(ValueError, match="requires 'url'"):
        await client._connect_http()


async def test_connect_http_success(monkeypatch):
    monkeypatch.setattr(mcp_client, "_MCP_AVAILABLE", True)
    seen = {}

    def _http_client(**kwargs):
        seen.update(kwargs)
        return FakeTransportCM(("read", "write", "extra"))

    monkeypatch.setattr(mcp_client, "streamablehttp_client", _http_client)
    session = FakeSession(_init_result())
    monkeypatch.setattr(mcp_client, "ClientSession", lambda r, w: session)

    client = MCPClient(name="x", transport="streamable_http", url="http://u", headers={"A": "b"})
    await client._connect_http()
    assert seen == {"url": "http://u", "headers": {"A": "b"}}
    assert client.session is session


async def test_connect_sse_import_error(monkeypatch):
    # No stub installed: real `mcp.client.sse` import fails.
    monkeypatch.setitem(sys.modules, "mcp.client.sse", None)
    client = MCPClient(name="x", transport="sse", url="http://u")
    with pytest.raises(ImportError, match="SSE transport requires"):
        await client._connect_sse()


async def test_connect_sse_requires_url(monkeypatch):
    _install_mcp_stub(monkeypatch)
    client = MCPClient(name="x", transport="sse")
    with pytest.raises(ValueError, match="requires 'url'"):
        await client._connect_sse()


async def test_connect_sse_success(monkeypatch):
    seen = {}

    def _sse_client(**kwargs):
        seen.update(kwargs)
        return FakeTransportCM(("read", "write"))

    _install_mcp_stub(monkeypatch, sse_client=_sse_client)
    session = FakeSession(_init_result())
    monkeypatch.setattr(mcp_client, "ClientSession", lambda r, w: session)

    client = MCPClient(name="x", transport="sse", url="http://u", headers={"A": "b"})
    await client._connect_sse()
    assert seen == {"url": "http://u", "headers": {"A": "b"}}
    assert client.session is session


# ─── initialize / discovery ─────────────────────────────────────────────────


async def test_initialize_requires_session():
    client = MCPClient(name="x")
    with pytest.raises(RuntimeError, match="Session not established"):
        await client._initialize()


async def test_initialize_with_capabilities_model_dump():
    caps = SimpleNamespace(model_dump=lambda: {"tools": {}})
    session = FakeSession(
        _init_result(caps),
        list_tools_page=SimpleNamespace(tools=[], nextCursor=None),
    )
    client = MCPClient(name="x")
    client.session = session
    await client._initialize()
    assert client._server_info == {
        "name": "srv",
        "version": "1.0",
        "protocol_version": "2024-11-05",
        "capabilities": {"tools": {}},
    }


async def test_initialize_capabilities_without_model_dump():
    caps = object()  # no model_dump attribute
    session = FakeSession(_init_result(caps))
    client = MCPClient(name="x")
    client.session = session
    await client._initialize()
    assert client._server_info["capabilities"] == {}


async def test_discover_capabilities_all_sections():
    raw_tools = SimpleNamespace(tools=[_raw_tool("t1", title="T1", annotations={"x": 1})])
    raw_resources = SimpleNamespace(
        resources=[SimpleNamespace(uri="u1", name="n1", description="d", mimeType="text/plain")]
    )
    raw_prompts = SimpleNamespace(
        prompts=[
            SimpleNamespace(
                name="p1",
                description="pd",
                arguments=[SimpleNamespace(name="a1", description="ad")],
            ),
            SimpleNamespace(name="p2", description=None, arguments=[]),
        ]
    )
    session = FakeSession(
        list_tools_page=raw_tools,
        list_resources_result=raw_resources,
        list_prompts_result=raw_prompts,
    )
    client = MCPClient(name="x")
    client.session = session
    client._server_info = {"capabilities": {"tools": {}, "resources": {}, "prompts": {}}}
    await client._discover_capabilities()

    assert client.tools["t1"].title == "T1"
    assert client.tools["t1"].annotations == {"x": 1}
    assert client.resources["u1"].mimeType == "text/plain"
    assert client.prompts["p1"].arguments[0].name == "a1"
    assert client.prompts["p2"].arguments is None


async def test_discover_capabilities_handles_errors():
    session = FakeSession(
        list_tools_error=RuntimeError("boom"),
        list_resources_error=RuntimeError("boom"),
        list_prompts_error=RuntimeError("boom"),
    )
    client = MCPClient(name="x")
    client.session = session
    client._server_info = {"capabilities": {"tools": {}, "resources": {}, "prompts": {}}}
    await client._discover_capabilities()
    assert client.tools == {}
    assert client.resources == {}
    assert client.prompts == {}


async def test_discover_capabilities_no_caps():
    client = MCPClient(name="x")
    client.session = FakeSession()
    client._server_info = {"capabilities": {}}
    await client._discover_capabilities()
    assert client.tools == {}


# ─── list_tools ─────────────────────────────────────────────────────────────


async def test_list_tools_not_connected():
    client = MCPClient(name="x")
    with pytest.raises(RuntimeError, match="Not connected"):
        await client.list_tools()


async def test_list_tools_single_page():
    session = FakeSession(list_tools_page=SimpleNamespace(tools=[_raw_tool("a")], nextCursor=None))
    client = MCPClient(name="x")
    client.session = session
    tools = await client.list_tools()
    assert [t.name for t in tools] == ["a"]
    assert client.tools["a"].description == "desc"
    assert session.list_tools_calls == [{}]


async def test_list_tools_pagination():
    class PagedSession(FakeSession):
        async def list_tools(self, **kwargs):
            self.list_tools_calls.append(kwargs)
            if kwargs.get("cursor") == "c1":
                return SimpleNamespace(tools=[_raw_tool("b")], nextCursor=None)
            return SimpleNamespace(tools=[_raw_tool("a")], nextCursor="c1")

    session = PagedSession()
    client = MCPClient(name="x")
    client.session = session
    tools = await client.list_tools()
    assert [t.name for t in tools] == ["a", "b"]
    assert session.list_tools_calls == [{}, {"cursor": "c1"}]


# ─── call_tool / validation ─────────────────────────────────────────────────


async def test_call_tool_not_connected():
    client = MCPClient(name="x")
    with pytest.raises(RuntimeError, match="Not connected"):
        await client.call_tool("t", {})


async def test_call_tool_success_and_lists_tools():
    result = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="ok", data=None, mimeType=None, uri=None),
            SimpleNamespace(type="image", text=None, data="aGk=", mimeType="image/png", uri=None),
        ],
        isError=False,
    )
    session = FakeSession(call_tool_result=result)
    client = MCPClient(name="x")
    client.session = session
    out = await client.call_tool("t", {"a": 1})
    assert out.isError is False
    assert out.content[0].text == "ok"
    assert out.content[1].data == "aGk="
    assert session.tool_calls == [("t", {"a": 1})]


async def test_call_tool_validation_rejects_missing_required():
    session = FakeSession()
    client = MCPClient(name="x")
    client.session = session
    client.tools["t"] = MCPTool(
        name="t",
        description="d",
        inputSchema={"type": "object", "properties": {"a": {}}, "required": ["a"]},
    )
    out = await client.call_tool("t", {})
    assert out.isError is True
    assert "missing required argument" in out.content[0].text
    assert session.tool_calls == []


async def test_call_tool_error_wrapped():
    session = FakeSession(call_tool_error=RuntimeError("kaboom"))
    client = MCPClient(name="x")
    client.session = session
    out = await client.call_tool("t", {})
    assert out.isError is True
    assert "kaboom" in out.content[0].text


def test_validate_arguments_non_dict_schema():
    assert MCPClient._validate_arguments("t", {}, ["not", "a", "dict"]) is None


def test_validate_arguments_non_object_schema():
    assert MCPClient._validate_arguments("t", {"x": 1}, {"type": "string"}) is None


def test_validate_arguments_additional_properties_blocked():
    schema = {"type": "object", "properties": {"a": {}}, "additionalProperties": False}
    with pytest.raises(ValueError, match="unexpected argument"):
        MCPClient._validate_arguments("t", {"a": 1, "b": 2}, schema)


def test_validate_arguments_additional_properties_allowed_by_default():
    schema = {"type": "object", "properties": {"a": {}}}
    assert MCPClient._validate_arguments("t", {"a": 1, "b": 2}, schema) is None


def test_validate_arguments_required_satisfied():
    schema = {"type": "object", "properties": {"a": {}, "b": {}}, "required": ["a", "b"]}
    assert MCPClient._validate_arguments("t", {"a": 1, "b": 2}, schema) is None


# ─── resources / prompts ────────────────────────────────────────────────────


async def test_list_resources_not_connected():
    client = MCPClient(name="x")
    with pytest.raises(RuntimeError, match="Not connected"):
        await client.list_resources()


async def test_list_resources_success():
    result = SimpleNamespace(
        resources=[SimpleNamespace(uri="u", name="n", description="d", mimeType="text/plain")]
    )
    session = FakeSession(list_resources_result=result)
    client = MCPClient(name="x")
    client.session = session
    resources = await client.list_resources()
    assert resources[0].uri == "u"
    assert client.resources["u"].description == "d"


async def test_read_resource_not_connected():
    client = MCPClient(name="x")
    with pytest.raises(RuntimeError, match="Not connected"):
        await client.read_resource("u")


async def test_read_resource_text_and_blob():
    result = SimpleNamespace(
        contents=[
            SimpleNamespace(text="line1"),
            SimpleNamespace(blob=b"\x00", mimeType="image/png"),
            SimpleNamespace(blob=b"\x01", mimeType=None),  # unknown mime type
            SimpleNamespace(),  # neither text nor blob: skipped
            SimpleNamespace(text="line2"),
        ]
    )
    session = FakeSession(read_resource_result=result)
    client = MCPClient(name="x")
    client.session = session
    out = await client.read_resource("u")
    assert out == "line1\n[binary: image/png]\n[binary: unknown]\nline2"


async def test_list_prompts_not_connected():
    client = MCPClient(name="x")
    with pytest.raises(RuntimeError, match="Not connected"):
        await client.list_prompts()


async def test_list_prompts_success_with_and_without_args():
    result = SimpleNamespace(
        prompts=[
            SimpleNamespace(
                name="p1",
                description="d",
                arguments=[SimpleNamespace(name="a", description="ad")],
            ),
            SimpleNamespace(name="p2", description=None),
        ]
    )
    session = FakeSession(list_prompts_result=result)
    client = MCPClient(name="x")
    client.session = session
    prompts = await client.list_prompts()
    assert prompts[0].arguments[0].description == "ad"
    assert prompts[1].arguments is None
    assert client.prompts["p1"].name == "p1"


async def test_get_prompt_not_connected():
    client = MCPClient(name="x")
    with pytest.raises(RuntimeError, match="Not connected"):
        await client.get_prompt("p")


async def test_get_prompt_variants():
    result = SimpleNamespace(
        messages=[
            SimpleNamespace(content=SimpleNamespace(text="hello")),
            SimpleNamespace(content={"text": "from-dict"}),
            SimpleNamespace(content=None),
            SimpleNamespace(content={"no_text": 1}),
        ]
    )
    session = FakeSession(get_prompt_result=result)
    client = MCPClient(name="x")
    client.session = session
    out = await client.get_prompt("p", {"x": 1})
    assert out == "hello\nfrom-dict\n"


async def test_get_prompt_without_arguments():
    result = SimpleNamespace(messages=[SimpleNamespace(content=SimpleNamespace(text="hi"))])
    session = FakeSession(get_prompt_result=result)
    client = MCPClient(name="x")
    client.session = session
    assert await client.get_prompt("p") == "hi"


# ─── notifications ──────────────────────────────────────────────────────────


async def test_subscribe_and_unsubscribe():
    client = MCPClient(name="x")

    async def cb(*_a, **_k):
        return None

    await client.subscribe("chan", cb)
    assert client._notification_handlers["chan"] == [cb]
    await client.subscribe("chan", cb)  # channel already present
    assert client._notification_handlers["chan"] == [cb, cb]
    await client.unsubscribe("chan", cb)
    await client.unsubscribe("chan", cb)
    assert client._notification_handlers["chan"] == []
    # Unsubscribing a missing handler is a no-op.
    await client.unsubscribe("chan", cb)
    await client.unsubscribe("missing", cb)


# ─── close / legacy ─────────────────────────────────────────────────────────


async def test_close_tears_down_session_and_transport():
    session = FakeSession()
    cm = FakeTransportCM(("r", "w"))
    client = MCPClient(name="x")
    client.session = session
    client._connect_cm = cm
    client._notification_handlers["c"] = []
    await client.close()
    assert client.session is None
    assert client._connect_cm is None
    assert client._notification_handlers == {}
    assert session.exit_count == 1
    assert cm.exited == 1


async def test_close_suppresses_session_and_cm_errors():
    session = FakeSession(close_error=RuntimeError("bad"))

    class BadCM(FakeTransportCM):
        async def __aexit__(self, *exc):
            raise RuntimeError("cm bad")

    client = MCPClient(name="x")
    client.session = session
    client._connect_cm = BadCM(("r", "w"))
    await client.close()
    assert client.session is None


async def test_close_with_no_session_or_transport():
    client = MCPClient(name="x")
    await client.close()
    assert client.session is None
    assert client._connect_cm is None


async def test_close_with_session_but_no_transport():
    session = FakeSession()
    client = MCPClient(name="x")
    client.session = session
    await client.close()
    assert client.session is None
    assert session.exit_count == 1


async def test_start_and_stop_delegate(monkeypatch):
    client = MCPClient(name="x")
    calls = []

    async def _connect():
        calls.append("connect")

    async def _close():
        calls.append("close")

    monkeypatch.setattr(client, "connect", _connect)
    monkeypatch.setattr(client, "close", _close)
    await client.start()
    await client.stop()
    assert calls == ["connect", "close"]


def test_get_tool_definitions():
    client = MCPClient(name="x")
    client.tools = {
        "a": MCPTool(name="a", description="da", inputSchema={"type": "object"}),
        "b": MCPTool(name="b", description="db", inputSchema={"type": "object"}),
    }
    defs = client.get_tool_definitions()
    assert len(defs) == 2
    assert defs[0]["type"] == "function"
    assert defs[0]["function"]["name"] in {"a", "b"}


# ─── MCPRegistry ────────────────────────────────────────────────────────────


def test_registry_register_and_get():
    registry = MCPRegistry()
    client = MCPClient(name="srv")
    registry.register(client)
    assert registry.get_client("srv") is client
    assert registry.get_client("missing") is None


def test_registry_register_default_name():
    registry = MCPRegistry()
    client = MCPClient(name="")
    registry.register(client)
    assert registry.get_client("default") is client


async def test_registry_start_all_collects_errors(monkeypatch):
    registry = MCPRegistry()
    ok = MCPClient(name="ok")
    bad = MCPClient(name="bad")

    async def _ok_connect():
        return None

    async def _bad_connect():
        raise RuntimeError("nope")

    monkeypatch.setattr(ok, "connect", _ok_connect)
    monkeypatch.setattr(bad, "connect", _bad_connect)
    registry.register(ok)
    registry.register(bad)
    await registry.start_all()  # must not raise


async def test_registry_stop_all_and_clear(monkeypatch):
    registry = MCPRegistry()
    ok = MCPClient(name="ok")
    bad = MCPClient(name="bad")

    async def _ok_close():
        return None

    async def _bad_close():
        raise RuntimeError("nope")

    monkeypatch.setattr(ok, "close", _ok_close)
    monkeypatch.setattr(bad, "close", _bad_close)
    registry.register(ok)
    registry.register(bad)
    await registry.stop_all()
    assert registry.get_client("ok") is None


def test_registry_list_tools():
    registry = MCPRegistry()
    client = MCPClient(name="srv")
    client.tools = {"t": MCPTool(name="t", description="d", inputSchema={"type": "object"})}
    registry.register(client)
    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "t"
