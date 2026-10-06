"""Regression: _check_sandbox must enforce restricted paths for list_files.

The canonical _FILE_TOOLS table maps list_directory -> ("dir", "read"), but
the native ``list_files`` tool takes a ``directory`` parameter
(app/tools/builtins.py).  The parameter-key gap made _check_sandbox skip
validate_file_access entirely for list_files calls (see
docs/plans/report-backlog.md B.2).
"""

from __future__ import annotations

from app.core.engine.validation import _check_sandbox


class _FakeSandbox:
    def __init__(self) -> None:
        self.checked: list[tuple[str, str]] = []

    def validate_file_access(self, path: str, mode: str):
        self.checked.append((path, mode))
        if path.startswith("/etc"):
            return False, "path not allowed"
        return True, "OK"

    def validate_command(self, cmd: str):
        return True, "OK"


def test_check_sandbox_enforces_list_files_directory_param() -> None:
    sandbox = _FakeSandbox()
    allowed, reason = _check_sandbox(sandbox, "list_files", {"directory": "/etc"})
    assert not allowed
    assert "not allowed" in reason
    assert sandbox.checked == [("/etc", "read")]


def test_check_sandbox_enforces_list_directory_dir_param() -> None:
    sandbox = _FakeSandbox()
    allowed, _ = _check_sandbox(sandbox, "list_directory", {"dir": "/etc"})
    assert not allowed
    assert sandbox.checked == [("/etc", "read")]


def test_check_sandbox_still_allows_unrestricted_list_files() -> None:
    sandbox = _FakeSandbox()
    allowed, reason = _check_sandbox(sandbox, "list_files", {"directory": "/workspace"})
    assert allowed
    assert reason == "OK"


def test_check_sandbox_read_file_path_param_unchanged() -> None:
    sandbox = _FakeSandbox()
    allowed, _ = _check_sandbox(sandbox, "read_file", {"path": "/etc/passwd"})
    assert not allowed
    assert sandbox.checked == [("/etc/passwd", "read")]
