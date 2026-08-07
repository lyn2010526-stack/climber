"""Tests for tools registry."""

from __future__ import annotations

import pytest

from app.tools import ToolDefinition, ToolRegistry


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def setup_method(self):
        self.registry = ToolRegistry()

    def test_register_tool(self):
        def my_tool(x: int) -> str:
            return str(x)

        self.registry.register("my_tool", "A tool", {"type": "object"}, my_tool)
        assert "my_tool" in self.registry._tools
        assert "my_tool" in self.registry._definitions

    def test_unregister_tool(self):
        def my_tool(x: int) -> str:
            return str(x)

        self.registry.register("my_tool", "A tool", {"type": "object"}, my_tool)
        result = self.registry.unregister("my_tool")
        assert result is True
        assert "my_tool" not in self.registry._tools

    def test_unregister_nonexistent(self):
        result = self.registry.unregister("nonexistent")
        assert result is False

    def test_list_tools(self):
        def tool1(x: int) -> str:
            return str(x)

        def tool2(y: str) -> str:
            return y

        self.registry.register("tool1", "Tool 1", {}, tool1)
        self.registry.register("tool2", "Tool 2", {}, tool2)
        tools = self.registry.list_tools()
        assert len(tools) == 2

    def test_get_tool(self):
        def my_tool(x: int) -> str:
            return str(x)

        self.registry.register("my_tool", "A tool", {}, my_tool)
        tool = self.registry.get_tool("my_tool")
        assert tool is not None
        assert tool.name == "my_tool"

    def test_get_tool_nonexistent(self):
        tool = self.registry.get_tool("nonexistent")
        assert tool is None

    def test_decorator_registration(self):
        @self.registry.tool(name="decorated_tool", description="A decorated tool")
        def my_func(x: int) -> str:
            return str(x)

        assert "decorated_tool" in self.registry._tools

    def test_decorator_infers_name(self):
        @self.registry.tool()
        def auto_named_tool(x: int) -> str:
            return str(x)

        assert "auto_named_tool" in self.registry._tools

    def test_infer_schema_int_param(self):
        def my_func(x: int) -> str:
            return str(x)

        schema = self.registry._infer_schema(my_func)
        assert schema["properties"]["x"]["type"] == "integer"

    def test_infer_schema_float_param(self):
        def my_func(x: float) -> str:
            return str(x)

        schema = self.registry._infer_schema(my_func)
        assert schema["properties"]["x"]["type"] == "number"

    def test_infer_schema_bool_param(self):
        def my_func(x: bool) -> str:
            return str(x)

        schema = self.registry._infer_schema(my_func)
        assert schema["properties"]["x"]["type"] == "boolean"

    def test_infer_schema_str_param(self):
        def my_func(x: str) -> str:
            return x

        schema = self.registry._infer_schema(my_func)
        assert schema["properties"]["x"]["type"] == "string"

    def test_infer_schema_no_annotation(self):
        def my_func(x):
            return x

        schema = self.registry._infer_schema(my_func)
        assert schema["properties"]["x"]["type"] == "string"

    def test_infer_schema_required(self):
        def my_func(x: int, y: str = "default") -> str:
            return str(x) + y

        schema = self.registry._infer_schema(my_func)
        assert "x" in schema["required"]
        assert "y" not in schema["required"]

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        def my_tool(x: int) -> str:
            return f"result: {x}"

        self.registry.register("my_tool", "A tool", {}, my_tool)
        result = await self.registry.execute("my_tool", {"x": 42})
        assert result == "result: 42"

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self):
        with pytest.raises(ValueError):
            await self.registry.execute("nonexistent", {})

    @pytest.mark.asyncio
    async def test_execute_async_tool(self):
        async def async_tool(x: int) -> str:
            return f"async: {x}"

        self.registry.register("async_tool", "Async tool", {}, async_tool)
        result = await self.registry.execute("async_tool", {"x": 10})
        assert result == "async: 10"


class TestToolDefinition:
    """Tests for ToolDefinition."""

    def test_create_definition(self):
        definition = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object"},
            type="function",
        )
        assert definition.name == "test_tool"
        assert definition.description == "A test tool"
        assert definition.type == "function"

    def test_definition_default_type(self):
        definition = ToolDefinition(
            name="test_tool",
            description="Test",
            parameters={},
        )
        assert definition.type == "function"
