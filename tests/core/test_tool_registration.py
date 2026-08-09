from app.tools import get_tool_registry, register_builtins


def test_register_builtins_loads_available_tool_modules() -> None:
    register_builtins()

    assert get_tool_registry().get_tool("get_datetime") is not None
    assert get_tool_registry().get_tool("browser_navigate") is not None
