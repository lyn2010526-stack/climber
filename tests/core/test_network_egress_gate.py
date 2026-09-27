"""Network egress gate tests.

`SandboxConfig.enable_network` (app/core/sandbox.py:190) only strips proxy
variables from the subprocess environment, so a child process can still reach
the network directly. `SecurityConfig.enable_network`
(app/core/security_sandbox.py:256) is a declared field with no reader at all.

Neither one gates the tools that actually perform egress: `web_search` and
`fetch_url` are plain async functions in app/tools/builtins.py that call
httpx directly and never touch a sandbox. A deployment that sets
enable_network=False still has working outbound network access through the
agent tool path.

The gate is enforced in ToolRegistry.execute, the single choke point every
tool call passes through, so it covers the registered network tools without
editing each one. These tests pin that behaviour.
"""

from __future__ import annotations

import pytest

from app.tools import ToolRegistry


def make_network_tool() -> object:
    calls: list[str] = []

    async def fake_fetch(url: str) -> str:
        calls.append(url)
        return "fetched"

    # Named after a real gated tool so the test exercises the production
    # set rather than a locally overridden copy.
    fake_fetch.__name__ = "web_search"
    return fake_fetch, calls


def build_registry(tool, *prop_names: str) -> ToolRegistry:
    props = {name: {"type": "string"} for name in (prop_names or ("url",))}
    registry = ToolRegistry()
    registry.register(
        tool.__name__,
        "a tool that performs network egress",
        {"type": "object", "properties": props},
        tool,
    )
    return registry


@pytest.fixture(autouse=True)
def open_gate():
    """Start each test with egress allowed unless it says otherwise.

    The per-test restore is handled by the session-wide reset_network_gate
    fixture in tests/conftest.py. NETWORK_TOOLS is never overridden here: the
    production set is the contract under test.
    """
    ToolRegistry.set_network_enabled(True)


@pytest.mark.asyncio
async def test_network_tool_runs_when_network_is_enabled() -> None:
    tool, calls = make_network_tool()
    registry = build_registry(tool)

    result = await registry.execute("web_search", {"url": "https://example.com"})

    assert result == "fetched"
    assert calls == ["https://example.com"]


@pytest.mark.asyncio
async def test_network_tool_is_blocked_when_network_is_disabled() -> None:
    tool, calls = make_network_tool()
    registry = build_registry(tool)
    ToolRegistry.set_network_enabled(False)

    result = await registry.execute("web_search", {"url": "https://example.com"})

    assert "network" in result.lower()
    assert calls == [], "the tool must not run at all, not fail after egress"


@pytest.mark.asyncio
async def test_blocked_message_tells_the_model_the_reason() -> None:
    """The tool result is fed back to the LLM, so it has to be actionable."""
    tool, _ = make_network_tool()
    registry = build_registry(tool)
    ToolRegistry.set_network_enabled(False)

    result = await registry.execute("web_search", {"url": "https://example.com"})

    assert "web_search" in result
    assert "disabled" in result.lower()


@pytest.mark.asyncio
async def test_local_tools_are_unaffected_by_the_gate() -> None:
    async def local_echo(text: str) -> str:
        return text

    local_echo.__name__ = "local_echo"
    registry = build_registry(local_echo)
    ToolRegistry.set_network_enabled(False)
    assert await registry.execute("local_echo", {"text": "hi"}) == "hi"


@pytest.mark.asyncio
async def test_gating_does_not_touch_tools_that_are_not_in_the_set() -> None:
    """A tool absent from NETWORK_TOOLS must still run with the gate closed.

    This is the counterweight to the coverage test: the gate is a deny-list
    over registered names, so an unrelated tool must not be collateral damage.
    """
    async def read_something(path: str) -> str:
        return f"read {path}"

    read_something.__name__ = "read_something"
    registry = build_registry(read_something, "path")
    ToolRegistry.set_network_enabled(False)

    result = await registry.execute("read_something", {"path": "fixture.txt"})

    assert result == "read fixture.txt"


def test_gate_defaults_to_the_environment_setting() -> None:
    import os

    from app.tools import ToolRegistry as TR

    os.environ["CLIMBER_ENABLE_NETWORK"] = "0"
    try:
        assert TR.network_enabled_from_env() is False
        os.environ["CLIMBER_ENABLE_NETWORK"] = "false"
        assert TR.network_enabled_from_env() is False
        os.environ["CLIMBER_ENABLE_NETWORK"] = "1"
        assert TR.network_enabled_from_env() is True
    finally:
        os.environ.pop("CLIMBER_ENABLE_NETWORK", None)


def test_unknown_env_value_fails_closed() -> None:
    """An unparsable setting must block egress rather than allow it."""
    import os

    os.environ["CLIMBER_ENABLE_NETWORK"] = "maybe"
    try:
        assert ToolRegistry.network_enabled_from_env() is False
    finally:
        os.environ.pop("CLIMBER_ENABLE_NETWORK", None)


def test_every_registered_network_tool_is_declared() -> None:
    """NETWORK_TOOLS must match the tools that really open a socket.

    The set was wrong twice while this gate was being built: `research` was
    declared but never registered, and `download_file` and `translate` were
    doing real httpx calls while missing from the set. Deriving the expectation
    from the callable source turns a silent coverage hole into a failure.
    """
    import importlib
    import inspect

    importlib.import_module("app.tools.builtins")
    importlib.import_module("app.tools.native_tools")
    from app.tools import get_tool_registry

    registry = get_tool_registry()
    network_markers = ("httpx", "requests", "socket.", "playwright", "aiohttp")

    detected = set()
    for name, func in registry._tools.items():
        try:
            source = inspect.getsource(func)
        except (OSError, TypeError):
            continue
        if any(marker in source for marker in network_markers):
            detected.add(name)

    assert detected, "detection found no network tools at all; check the scan"
    ungated = detected - ToolRegistry.NETWORK_TOOLS
    assert not ungated, f"tools perform network I/O but are not gated: {sorted(ungated)}"


def test_declared_network_tools_all_exist() -> None:
    """A declared name that is not registered is a stale entry, not a gate."""
    import importlib

    importlib.import_module("app.tools.builtins")
    importlib.import_module("app.tools.native_tools")
    from app.tools import get_tool_registry

    registered = set(get_tool_registry()._tools)
    ghost = sorted(ToolRegistry.NETWORK_TOOLS - registered)
    assert not ghost, f"NETWORK_TOOLS declares unregistered tools: {ghost}"


@pytest.mark.asyncio
async def test_gate_state_does_not_leak_between_tests() -> None:
    """A test that closes the gate must not close it for the rest of the run.

    The gate is class-level state. Without the reset_network_gate fixture in
    conftest, this test would leave egress disabled and make every later
    network-dependent test fail depending on execution order.
    """
    ToolRegistry.set_network_enabled(False)
    assert ToolRegistry.network_enabled() is False

    # Simulate what the autouse fixture guarantees on teardown.
    ToolRegistry.set_network_enabled(True)
    assert ToolRegistry.network_enabled() is True
