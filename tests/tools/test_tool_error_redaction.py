"""Regression tests for safe tool execution error reporting."""

from __future__ import annotations

import pytest

from app.tools import ToolRegistry, builtins, logger, native_tools


@pytest.mark.asyncio
async def test_registry_redacts_secrets_from_returned_error_and_log(monkeypatch):
    registry = ToolRegistry()

    async def failing_tool() -> str:
        raise RuntimeError(
            "request failed: api_key=top-secret-token password=hunter2"
        )

    registry.register("failing", "Fail", {"type": "object"}, failing_tool)
    logged: list[dict[str, object]] = []
    monkeypatch.setattr(
        logger,
        "error",
        lambda *_args, **kwargs: logged.append(kwargs),
    )

    result = await registry.execute("failing", {})

    assert result == "Error executing failing: request failed: api_key=[REDACTED] password=[REDACTED]"
    assert logged == [
        {
            "tool": "failing",
            "error_type": "RuntimeError",
            "error": "request failed: api_key=[REDACTED] password=[REDACTED]",
        }
    ]


@pytest.mark.asyncio
async def test_registry_preserves_ordinary_tool_failure_text():
    registry = ToolRegistry()

    async def failing_tool() -> str:
        raise ValueError("input must be an integer")

    registry.register("failing", "Fail", {"type": "object"}, failing_tool)

    assert await registry.execute("failing", {}) == (
        "Error executing failing: input must be an integer"
    )


@pytest.mark.asyncio
async def test_native_tool_redacts_exception_text(monkeypatch):
    monkeypatch.setattr(
        "webbrowser.open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("authorization: Bearer native-secret-token")
        ),
    )

    result = await native_tools.open_browser("https://example.com")

    assert result == "Error: authorization: [REDACTED]"


@pytest.mark.asyncio
async def test_builtin_tool_preserves_ordinary_failure_text(tmp_path):
    missing_path = tmp_path / "missing.txt"

    result = await builtins.read_file(str(missing_path))

    assert result.startswith("Error reading file: ")
    assert "No such file or directory" in result


@pytest.mark.asyncio
async def test_builtin_tool_redacts_exception_text(monkeypatch):
    def fail(*_args, **_kwargs):
        raise RuntimeError("secret=calculator-secret")

    monkeypatch.setattr(builtins, "_safe_eval_math", fail)

    result = await builtins.calculator("1 + 1")

    assert result == "Error: secret=[REDACTED]"
