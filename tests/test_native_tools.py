"""Tests for native_tools registration and safety behaviors."""

from __future__ import annotations

import pytest

from app.tools import register_builtins, tool_registry
from app.tools.native_tools import (
    _pyautogui_available,
    _validate_command_safety,
    native_run,
    process_video,
    take_screenshot,
)


def test_native_tools_registered():
    """The native desktop/media tools must be present in the registry."""
    register_builtins()

    names = {t.name for t in tool_registry.list_tools()}
    for expected in ("native_run", "native_read_file", "native_write_file",
                     "open_browser", "take_screenshot", "click_mouse",
                     "type_text", "process_video", "process_image",
                     "download_file"):
        assert expected in names, f"tool {expected} not registered"


def test_validate_command_safety_rejects_shell_metacharacters():
    safe, _ = _validate_command_safety("echo hello")
    assert safe is True
    for bad in ("ls; rm -rf /", "cat /etc/passwd | head", "echo $(whoami)",
                "echo `whoami`", "a && b", "a || b"):
        safe, reason = _validate_command_safety(bad)
        assert safe is False, f"{bad!r} should be rejected"
        assert reason


def test_pyautogui_available_is_false_without_display(monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    assert _pyautogui_available() is False


@pytest.mark.asyncio
async def test_take_screenshot_returns_clear_error_without_display(monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    result = await take_screenshot("/tmp/opencode/nope.png")
    assert "no DISPLAY" in result


@pytest.mark.asyncio
async def test_native_run_rejects_dangerous_rm():
    result = await native_run("rm -rf /etc", timeout=10)
    assert "Command rejected" in result


@pytest.mark.asyncio
async def test_native_run_allowlist_blocks_unknown_binary():
    result = await native_run("some_unknown_bin_xyz --help", timeout=10)
    assert "not in the allowed binaries" in result


@pytest.mark.asyncio
async def test_process_video_requires_ffmpeg():
    import shutil
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed")
    result = await process_video("-version")
    assert "ffmpeg version" in result
