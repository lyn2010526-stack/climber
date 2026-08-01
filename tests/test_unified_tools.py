"""Tests for the unified tool abstraction layer."""

from __future__ import annotations

import pytest

from app.core.unified_tool_interface import (
    ToolCategory,
    ToolSource,
    UnifiedToolDefinition,
    UnifiedToolRegistry,
    UnifiedToolResult,
)


class TestUnifiedToolDefinition:
    def test_to_openai_format(self) -> None:
        tool = UnifiedToolDefinition(
            name="read_file",
            description="Read a file",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}},
        )
        fmt = tool.to_openai_format()
        assert fmt["type"] == "function"
        assert fmt["function"]["name"] == "read_file"

    def test_to_dict(self) -> None:
        tool = UnifiedToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={},
            source=ToolSource.LOCAL,
            category=ToolCategory.FILE,
        )
        data = tool.to_dict()
        assert data["name"] == "test_tool"
        assert data["source"] == "local"
        assert data["category"] == "file"


class TestUnifiedToolRegistry:
    async def _dummy_handler(self, **kwargs) -> str:
        return "result"

    def test_register_and_get(self) -> None:
        registry = UnifiedToolRegistry()
        tool = registry.register(
            name="test_tool",
            description="Test",
            parameters={},
            handler=self._dummy_handler,
        )
        assert tool.name == "test_tool"
        assert registry.get("test_tool") is not None

    def test_unregister(self) -> None:
        registry = UnifiedToolRegistry()
        registry.register("test", "Desc", {}, self._dummy_handler)
        assert registry.unregister("test")
        assert registry.get("test") is None

    def test_list_all(self) -> None:
        registry = UnifiedToolRegistry()
        registry.register("tool1", "Desc", {}, self._dummy_handler)
        registry.register("tool2", "Desc", {}, self._dummy_handler)
        assert len(registry.list_all()) == 2

    def test_list_by_source(self) -> None:
        registry = UnifiedToolRegistry()
        registry.register(
            "local_tool", "Desc", {}, self._dummy_handler, source=ToolSource.LOCAL
        )
        registry.register(
            "mcp_tool", "Desc", {}, self._dummy_handler, source=ToolSource.MCP
        )
        mcp_tools = registry.list_by_source(ToolSource.MCP)
        assert len(mcp_tools) == 1
        assert mcp_tools[0].name == "mcp_tool"

    def test_list_by_category(self) -> None:
        registry = UnifiedToolRegistry()
        registry.register(
            "file_tool", "Desc", {}, self._dummy_handler, category=ToolCategory.FILE
        )
        registry.register(
            "net_tool", "Desc", {}, self._dummy_handler, category=ToolCategory.NETWORK
        )
        file_tools = registry.list_by_category(ToolCategory.FILE)
        assert len(file_tools) == 1

    def test_set_enabled(self) -> None:
        registry = UnifiedToolRegistry()
        registry.register("test", "Desc", {}, self._dummy_handler)
        assert registry.set_enabled("test", False)
        tool = registry.get("test")
        assert tool is not None and not tool.is_enabled

    def test_list_enabled(self) -> None:
        registry = UnifiedToolRegistry()
        registry.register("enabled", "Desc", {}, self._dummy_handler)
        registry.register("disabled", "Desc", {}, self._dummy_handler)
        registry.set_enabled("disabled", False)
        enabled = registry.list_enabled()
        assert len(enabled) == 1
        assert enabled[0].name == "enabled"

    def test_get_openai_tools(self) -> None:
        registry = UnifiedToolRegistry()
        registry.register("tool1", "Desc", {}, self._dummy_handler)
        registry.register("tool2", "Desc", {}, self._dummy_handler)
        registry.set_enabled("tool2", False)
        tools = registry.get_openai_tools()
        assert len(tools) == 1

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        async def echo_handler(**kw) -> str:
            return "echoed"

        registry = UnifiedToolRegistry()
        registry.register("echo", "Echo input", {}, echo_handler)
        result = await registry.execute("echo", {})
        assert result.success
        assert result.output == "echoed"

    @pytest.mark.asyncio
    async def test_execute_not_found(self) -> None:
        registry = UnifiedToolRegistry()
        result = await registry.execute("nonexistent", {})
        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_disabled(self) -> None:
        registry = UnifiedToolRegistry()
        registry.register("disabled", "Desc", {}, lambda **kw: "result")
        registry.set_enabled("disabled", False)
        result = await registry.execute("disabled", {})
        assert not result.success
        assert "disabled" in result.error.lower()

    def test_get_stats(self) -> None:
        registry = UnifiedToolRegistry()
        registry.register(
            "local", "Desc", {}, self._dummy_handler, source=ToolSource.LOCAL
        )
        registry.register(
            "mcp", "Desc", {}, self._dummy_handler, source=ToolSource.MCP
        )
        stats = registry.get_stats()
        assert stats["total"] == 2
        assert "local" in stats["by_source"]
        assert "mcp" in stats["by_source"]

    def test_register_skill_tool(self) -> None:
        registry = UnifiedToolRegistry()
        registry.register(
            "skill_tool",
            "Desc",
            {},
            self._dummy_handler,
            source=ToolSource.SKILL,
            source_id="my_skill",
        )
        skill_tools = registry.list_by_skill("my_skill")
        assert len(skill_tools) == 1
        assert skill_tools[0].name == "skill_tool"

    def test_register_mcp_tool(self) -> None:
        registry = UnifiedToolRegistry()
        registry.register(
            "mcp_search",
            "Desc",
            {},
            self._dummy_handler,
            source=ToolSource.MCP,
            source_id="jcodemunch",
        )
        mcp_tools = registry.list_by_mcp("jcodemunch")
        assert len(mcp_tools) == 1
