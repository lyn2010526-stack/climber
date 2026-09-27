"""File-tool classification drift: the PLAN-mode write gate.

``_FILE_TOOLS`` drives the PLAN-mode read-only check, the overlay action choice,
and the sandbox file-access check. Two defects were found by reconciling the
table against the tools that are actually registered:

1. The table listed ``list_directory`` - a tool that does not exist - while the
   real ``list_files`` (parameter ``directory``) was unclassified, so PLAN mode
   never inspected it.
2. Genuine write tools were missing entirely: ``apply_patch`` and
   ``download_file`` (which writes arbitrary bytes to an arbitrary path and
   creates parent directories). PLAN mode let all of them through because an
   unclassified tool is not a file tool.

Also pinned here: the two command tools that were still missing
(``stream_command``, ``container_exec``) and the invariant that the file table
never names a tool that is not registered.

Round 27 removed the native-prefixed clones (``native_read_file``,
``native_write_file``, ``native_list_dir``) as functional duplicates, so those
names are gone from the table; ``write_file``/``read_file``/``list_files``
remain the classified spellings.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core.engine.validation import _COMMAND_TOOLS, _FILE_TOOLS, _check_plan_mode
from app.core.security_sandbox import AgentMode

# Tools that must be classified as writes, with the argument the table records.
NEW_WRITE_TOOLS: list[tuple[str, str]] = [
    ("write_file", "path"),
    ("apply_patch", "file_path"),
    ("download_file", "output_path"),
]

# Tools whose recorded parameter had been wrong or whose name did not exist.
NEW_READ_TOOLS: list[tuple[str, str]] = [
    ("list_files", "directory"),
    ("read_file", "path"),
]


# ─── the write gate actually closes ─────────────────────────────────────────


@pytest.mark.parametrize(("tool_name", "param"), NEW_WRITE_TOOLS)
def test_write_tools_are_blocked_in_plan_mode(tool_name: str, param: str) -> None:
    assert tool_name in _FILE_TOOLS, f"{tool_name} is not classified as a file tool"
    assert _FILE_TOOLS[tool_name][1] == "write"
    allowed, reason = _check_plan_mode(AgentMode.PLAN, tool_name)
    assert allowed is False, f"{tool_name} was allowed to write in PLAN mode"
    assert "PLAN mode" in reason


@pytest.mark.parametrize(("tool_name", "param"), NEW_READ_TOOLS)
def test_read_tools_are_classified_with_their_real_parameter(tool_name: str, param: str) -> None:
    assert tool_name in _FILE_TOOLS, f"{tool_name} is not classified"
    recorded_param, mode = _FILE_TOOLS[tool_name]
    assert recorded_param == param, f"{tool_name} records the wrong parameter"
    assert mode == "read"
    # reads stay available in PLAN mode
    allowed, _ = _check_plan_mode(AgentMode.PLAN, tool_name)
    assert allowed is True


def test_phantom_list_directory_is_gone() -> None:
    """The table must not keep naming a tool that does not exist."""
    assert "list_directory" not in _FILE_TOOLS


# ─── the two command tools that were still ungated ──────────────────────────


@pytest.mark.parametrize("tool_name", ["stream_command", "container_exec"])
def test_command_tools_are_classified_and_blocked_in_plan_mode(tool_name: str) -> None:
    assert tool_name in _COMMAND_TOOLS, f"{tool_name} is not classified as a command tool"
    allowed, reason = _check_plan_mode(AgentMode.PLAN, tool_name)
    assert allowed is False
    assert "command execution is read-only" in reason


def test_act_mode_still_permits_writes() -> None:
    """The gate is a PLAN-mode restriction, not a blanket write ban."""
    for tool_name, _ in NEW_WRITE_TOOLS:
        allowed, _ = _check_plan_mode(AgentMode.ACT, tool_name)
        assert allowed is True, f"{tool_name} was blocked in ACT mode"


def test_none_agent_mode_keeps_legacy_shortcircuit() -> None:
    for tool_name, _ in NEW_WRITE_TOOLS:
        allowed, reason = _check_plan_mode(None, tool_name)
        assert allowed is True
        assert reason == "OK"


# ─── reconciliation against the real registry ──────────────────────────────


def test_file_table_names_only_registered_tools() -> None:
    """Every classified file tool must be a real registered tool.

    ``list_directory`` slipped through precisely because nothing checked the
    table against the registry.
    """
    from app.tools import get_tool_registry

    registered = {t.name for t in get_tool_registry().list_tools()}
    assert registered, "tool registry is empty; the test setup is wrong"
    unknown = sorted(set(_FILE_TOOLS) - registered)
    assert not unknown, f"_FILE_TOOLS names unregistered tools: {unknown}"


def test_write_tools_really_take_a_path_like_argument() -> None:
    """The recorded parameter must exist in the tool's own signature."""
    import inspect

    import app.tools.builtins as builtins_mod
    import app.tools.native_tools as native_mod

    for tool_name, param in NEW_WRITE_TOOLS + NEW_READ_TOOLS:
        func = getattr(builtins_mod, tool_name, None) or getattr(
            native_mod, tool_name, None
        )
        assert func is not None, f"{tool_name} has no implementation"
        params = inspect.signature(func).parameters
        assert param in params, (
            f"{tool_name} does not accept '{param}' (has {sorted(params)})"
        )


@pytest.mark.parametrize("tool_name", sorted(_COMMAND_TOOLS))
def test_command_tools_really_accept_a_command_argument(tool_name: str) -> None:
    """Each command tool must have a command-like parameter to validate.

    The four non-registered names in the set (bash/shell/command/execute_command)
    are defensive aliases kept for permission_rules matching, so they are
    exempted here rather than deleted.
    """
    import inspect

    import app.tools.builtins as builtins_mod
    import app.tools.native_tools as native_mod

    func = getattr(builtins_mod, tool_name, None) or getattr(native_mod, tool_name, None)
    if func is None:
        assert tool_name in {"bash", "shell", "command", "execute_command"}
        return
    params: dict[str, Any] = inspect.signature(func).parameters
    assert any(p in params for p in ("command", "cmd")), f"{tool_name} has no command param"
