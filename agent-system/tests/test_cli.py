"""CLI 入口端到端测试（确定性 mock，离线可复现）。

通过子进程运行 `agent-system/__main__.py`，模拟真实命令行调用。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _entry() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "__main__.py")


def _run(*extra: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, _entry(), *extra]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=90, cwd=_repo_root())  # noqa: S603


def test_cli_human_mode_returns_zero() -> None:
    proc = _run("--objective", "查询并按部门汇总")
    assert proc.returncode == 0, proc.stderr
    assert "记忆审计日志" in proc.stdout


def test_cli_json_is_machine_parseable() -> None:
    proc = _run("--json", "--objective", "查询并按部门汇总")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["report"]["status"] == "completed"
    assert data["report"]["tool_calls"] >= 1
    assert len(data["events"]) > 0
    assert any(s["kind"] == "incremental" for s in data["snapshots"])
