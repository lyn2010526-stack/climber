"""Tests for CapabilityRegistry taking over the tool execution entrypoint."""

from __future__ import annotations

from typing import Any

import pytest

import app.core.di as di
from app.core.capability.bridge import register_tool_capabilities
from app.core.capability.capability import CapabilityMeta, WrappedCapability
from app.core.capability.registry import CapabilityRegistry
from app.tools import ToolRegistry


@pytest.fixture(autouse=True)
def _di_scope():
    with di.create_scope("capability-takeover-test"):
        yield


def _tool_registry() -> ToolRegistry:
    registry = ToolRegistry()

    @registry.tool(name="echo", description="Echo input")
    async def echo(text: str) -> str:
        return f"echo:{text}"

    return registry


@pytest.mark.asyncio
async def test_execute_delegates_to_capability_registry():
    tools = _tool_registry()
    caps = CapabilityRegistry()
    caps.register(
        WrappedCapability(
            CapabilityMeta(
                id="echo", name="echo", description="marker", capability_type="tool"
            ),
            fn=lambda **kw: "via-capability",
        )
    )
    di.register("CapabilityRegistry", caps)

    result = await tools.execute("echo", {"text": "hi"})
    assert result == "via-capability"


@pytest.mark.asyncio
async def test_execute_falls_back_without_registry():
    tools = _tool_registry()
    result = await tools.execute("echo", {"text": "hi"})
    assert result == "echo:hi"


@pytest.mark.asyncio
async def test_execute_falls_back_when_capability_missing():
    tools = _tool_registry()
    di.register("CapabilityRegistry", CapabilityRegistry())

    result = await tools.execute("echo", {"text": "hi"})
    assert result == "echo:hi"


@pytest.mark.asyncio
async def test_capability_failure_returns_error_string_without_double_execution():
    tools = _tool_registry()
    calls = {"direct": 0}

    @tools.tool(name="fragile", description="counts direct executions")
    async def fragile() -> str:
        calls["direct"] += 1
        return "direct-result"

    caps = CapabilityRegistry()

    async def _boom(**kwargs: Any) -> Any:
        raise RuntimeError("capability exploded")

    caps.register(
        WrappedCapability(
            CapabilityMeta(
                id="fragile", name="fragile", description="fails", capability_type="tool"
            ),
            fn=_boom,
        )
    )
    di.register("CapabilityRegistry", caps)

    result = await tools.execute("fragile", {})
    assert result.startswith("Error executing fragile:")
    assert calls["direct"] == 0


@pytest.mark.asyncio
async def test_register_tool_capabilities_wraps_all_tools():
    tools = _tool_registry()
    tools.register_mcp_tool(
        name="mcp_search",
        description="MCP search",
        parameters={},
        mcp_client=type("C", (), {"name": "srv", "call_tool": staticmethod(lambda n, a: None)})(),
        mcp_tool_name="search",
    )
    caps = CapabilityRegistry()

    count = register_tool_capabilities(caps, tools)

    assert count == 2
    impls = caps.get_implementations("echo")
    assert len(impls) == 1
    assert impls[0].meta.capability_type == "tool"
    assert caps.get_implementations("mcp_search")[0].meta.capability_type == "mcp"

    result = await caps.execute("echo", text="hi")
    assert result == "echo:hi"


def test_register_tool_capabilities_is_idempotent():
    tools = _tool_registry()
    caps = CapabilityRegistry()

    register_tool_capabilities(caps, tools)
    register_tool_capabilities(caps, tools)

    assert len(caps.get_implementations("echo")) == 1


@pytest.mark.asyncio
async def test_arch_v2_capability_branch_registers_and_wraps(monkeypatch, tmp_path):
    from app import main

    tools = _tool_registry()
    di.register("ToolRegistry", tools)
    monkeypatch.setattr(main.settings, "enable_arch_v2", True)
    monkeypatch.setattr(main.settings, "enable_capability", True)

    handles = await main._init_arch_v2()
    assert handles is not None
    registry = handles["capability_registry"]
    assert registry.get_implementations("echo")
    assert di.resolve("CapabilityRegistry") is registry
