"""Tests for tool self-extension system."""

from __future__ import annotations

import pytest

from app.core.sandbox import SandboxConfig, SandboxExecutor
from app.core.tool_extender import ToolCreationRequest, ToolSelfExtender, get_tool_extender
from app.tools import tool_registry


@pytest.fixture(autouse=True)
def _cleanup_tools():
    """Remove any custom tools created during tests."""
    from app.tools import register_builtins
    register_builtins()
    known_before = {t.name for t in tool_registry.list_tools()}
    yield
    known_after = {t.name for t in tool_registry.list_tools()}
    for name in known_after - known_before:
        tool_registry.unregister(name)


class TestToolCreationRequest:
    def test_creation(self) -> None:
        req = ToolCreationRequest(
            name="test_tool",
            description="A test tool",
            code="async def test_tool(): return 'hello'",
        )
        assert req.name == "test_tool"
        assert req.parameters == {}


class TestToolSelfExtender:
    @pytest.mark.asyncio
    async def test_invalid_name(self) -> None:
        extender = ToolSelfExtender()
        req = ToolCreationRequest(
            name="123invalid",
            description="x",
            code="async def 123invalid(): pass",
        )
        result = await extender.create_tool(req)
        assert result.success is False
        assert "Invalid" in result.message

    @pytest.mark.asyncio
    async def test_duplicate_name(self) -> None:
        extender = ToolSelfExtender()
        req = ToolCreationRequest(
            name="read_file",
            description="duplicate",
            code="async def read_file(): pass",
        )
        result = await extender.create_tool(req)
        assert result.success is False
        assert "already exists" in result.message

    @pytest.mark.asyncio
    async def test_unsafe_code_blocked(self) -> None:
        extender = ToolSelfExtender()
        req = ToolCreationRequest(
            name="dangerous",
            description="x",
            code="async def dangerous(): import os; os.system('rm -rf /')",
            smoke_test_args={},
        )
        result = await extender.create_tool(req)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_simple_tool_creation(self) -> None:
        extender = ToolSelfExtender()
        req = ToolCreationRequest(
            name="greet_user",
            description="Greet a user by name",
            code="async def greet_user(name: str) -> str:\n    return f'Hello, {name}!'\n",
            parameters={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            smoke_test_args={"name": "World"},
        )
        result = await extender.create_tool(req)
        assert result.success is True, f"Failed: {result.message} | {result.test_output}"
        assert tool_registry.get_tool("greet_user") is not None

    @pytest.mark.asyncio
    async def test_tool_execution_after_creation(self) -> None:
        extender = ToolSelfExtender()
        req = ToolCreationRequest(
            name="double",
            description="Double a number",
            code="async def double(x: int) -> int:\n    return x * 2\n",
            parameters={
                "type": "object",
                "properties": {"x": {"type": "integer"}},
                "required": ["x"],
            },
            smoke_test_args={"x": 5},
        )
        result = await extender.create_tool(req)
        assert result.success is True

        # Now actually execute it
        output = await tool_registry.execute("double", {"x": 21})
        assert "42" in output

    @pytest.mark.asyncio
    async def test_list_self_created_tools(self) -> None:
        extender = ToolSelfExtender()
        tools_before = set(extender.list_self_created_tools())

        req = ToolCreationRequest(
            name="unique_counter",
            description="Count items",
            code="async def unique_counter(items: str) -> int:\n    return len(items.split(','))\n",
            parameters={
                "type": "object",
                "properties": {"items": {"type": "string"}},
                "required": ["items"],
            },
            smoke_test_args={"items": "a,b,c"},
        )
        await extender.create_tool(req)

        tools_after = set(extender.list_self_created_tools())
        assert "unique_counter" in tools_after
        assert "unique_counter" not in tools_before


class TestSandboxExecutor:
    @pytest.mark.asyncio
    async def test_basic_execution(self) -> None:
        sandbox = SandboxExecutor(SandboxConfig(timeout_seconds=10))
        result = await sandbox.execute("echo hello")
        assert "hello" in result

    @pytest.mark.asyncio
    async def test_blocked_command(self) -> None:
        sandbox = SandboxExecutor(SandboxConfig())
        result = await sandbox.execute("sudo rm -rf /")
        assert "Blocked" in result or "Error" in result

    @pytest.mark.asyncio
    async def test_python_execution(self) -> None:
        sandbox = SandboxExecutor(SandboxConfig(timeout_seconds=10))
        result = await sandbox.execute("python3 -c 'print(42)'")
        assert "42" in result


class TestGetToolExtender:
    def test_singleton(self) -> None:
        a = get_tool_extender()
        b = get_tool_extender()
        assert a is b
