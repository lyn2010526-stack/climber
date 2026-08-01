import pytest
from app.core.tool_runtime import ToolRuntime, ToolResult


@pytest.fixture
def runtime():
    return ToolRuntime()


@pytest.mark.asyncio
async def test_register_and_execute_local_tool(runtime):
    def add(a: int, b: int) -> int:
        return a + b

    runtime.register_local("add", "Add two numbers", {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}, add)
    result = await runtime.execute("add", {"a": 1, "b": 2})
    assert result.success
    assert result.output == 3


@pytest.mark.asyncio
async def test_execute_with_timeout(runtime):
    import asyncio
    async def slow():
        await asyncio.sleep(10)
        return "done"

    runtime.register_local("slow", "Slow tool", {}, slow, timeout=0.1)
    result = await runtime.execute("slow", {})
    assert not result.success
    assert "timeout" in result.error.lower()


@pytest.mark.asyncio
async def test_tool_not_found(runtime):
    result = await runtime.execute("nonexistent", {})
    assert not result.success
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_get_openai_schemas(runtime):
    def greet(name: str) -> str:
        return f"Hello {name}"

    runtime.register_local("greet", "Greet someone", {"type": "object", "properties": {"name": {"type": "string"}}}, greet)
    schemas = runtime.get_openai_tools()
    names = [s["function"]["name"] for s in schemas]
    assert "greet" in names
    greet_schema = next(s for s in schemas if s["function"]["name"] == "greet")
    assert greet_schema["function"]["description"] == "Greet someone"
    assert greet_schema["function"]["parameters"]["properties"]["name"]["type"] == "string"
