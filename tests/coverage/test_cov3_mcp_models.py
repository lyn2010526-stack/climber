"""Coverage tests for app.tools.mcp_models."""

from __future__ import annotations

from app.tools.mcp_models import (
    MCPContent,
    MCPPrompt,
    MCPPromptArgument,
    MCPResource,
    MCPServerInfo,
    MCPTool,
    MCPToolResult,
    MCPTransportType,
)


def test_mcp_tool_defaults_and_values():
    tool = MCPTool(name="search", description="d", inputSchema={"type": "object"})
    assert tool.title is None
    assert tool.annotations is None
    assert tool.inputSchema == {"type": "object"}

    tool2 = MCPTool(
        name="x",
        title="X",
        description="y",
        inputSchema={"type": "string"},
        annotations={"a": 1},
    )
    assert tool2.title == "X"
    assert tool2.annotations == {"a": 1}


def test_mcp_content_fields():
    c = MCPContent(type="text", text="hello")
    assert c.text == "hello"
    assert c.data is None
    assert c.mimeType is None
    assert c.uri is None

    binary = MCPContent(type="image", data="aGk=", mimeType="image/png")
    assert binary.data == "aGk="
    assert binary.mimeType == "image/png"


def test_tool_result_to_text_text_and_resource():
    result = MCPToolResult(
        content=[
            MCPContent(type="text", text="first"),
            MCPContent(type="resource", uri="file:///a"),
            MCPContent(type="text", text="second"),
        ]
    )
    assert result.isError is False
    assert result.to_text() == "first\n[resource: file:///a]\nsecond"


def test_tool_result_to_text_ignores_non_text_and_blank_text():
    result = MCPToolResult(
        content=[
            MCPContent(type="image", data="aGk="),
            MCPContent(type="text", text=""),
            MCPContent(type="resource"),  # no uri
            MCPContent(type="text", text="kept"),
        ]
    )
    assert result.to_text() == "kept"


def test_tool_result_to_text_empty():
    assert MCPToolResult(content=[]).to_text() == ""


def test_tool_result_error_flag():
    result = MCPToolResult(content=[MCPContent(type="text", text="boom")], isError=True)
    assert result.isError is True


def test_mcp_resource_defaults():
    r = MCPResource(uri="u", name="n")
    assert r.description is None
    assert r.mimeType is None
    r2 = MCPResource(uri="u", name="n", description="d", mimeType="text/plain")
    assert r2.description == "d"
    assert r2.mimeType == "text/plain"


def test_mcp_prompt_argument_defaults():
    a = MCPPromptArgument(name="arg")
    assert a.description is None
    assert a.required is False
    a2 = MCPPromptArgument(name="arg", description="d", required=True)
    assert a2.required is True


def test_mcp_prompt_defaults():
    p = MCPPrompt(name="p")
    assert p.description is None
    assert p.arguments is None
    args = [MCPPromptArgument(name="a")]
    p2 = MCPPrompt(name="p", description="d", arguments=args)
    assert p2.arguments == args


def test_mcp_server_info_capabilities_default():
    info = MCPServerInfo(name="srv", version="1.0", protocol_version="2024-11-05")
    assert info.capabilities == {}
    info2 = MCPServerInfo(
        name="srv", version="1.0", protocol_version="v", capabilities={"tools": {}}
    )
    assert info2.capabilities == {"tools": {}}


def test_mcp_transport_type_constants():
    assert MCPTransportType.STDIO == "stdio"
    assert MCPTransportType.STREAMABLE_HTTP == "streamable_http"
    assert MCPTransportType.SSE == "sse"
