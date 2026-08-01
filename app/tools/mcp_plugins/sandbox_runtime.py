"""MCP Plugin: Sandbox Runtime — isolated code/command execution.

Provides a restricted execution environment with path whitelists,
command blacklists, and resource limits.
"""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
from dataclasses import dataclass
from typing import Any


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False
    blocked: bool = False
    block_reason: str = ""


class SandboxRuntime:
    """Isolated execution environment with safety constraints."""

    BLOCKED_PATTERNS = [
        r"\brm\s+-rf\s+/",
        r"\bchmod\s+777",
        r"\bmkfs\b",
        r"\bdd\s+if=",
        r"\bshred\b",
        r"\bgit\s+push\s+--force",
        r"\bgit\s+push\s+-f\b",
        r":\(\)\s*{\s*:\|:&\s*};\s*:",
        r"\bcurl\b.*\|\s*sh",
        r"\bwget\b.*\|\s*sh",
    ]

    def __init__(
        self,
        allowed_paths: list[str] | None = None,
        timeout: int = 30,
        max_output: int = 10000,
    ):
        self._allowed_paths = allowed_paths or [
            os.getcwd(), "/workspace", "/tmp",
        ]
        self._timeout = timeout
        self._max_output = max_output

    def check_command(self, command: str) -> tuple[bool, str]:
        """Check if a command is safe to execute."""
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, command):
                return False, f"Blocked by safety rule: pattern '{pattern}'"
        return True, ""

    async def execute(self, command: str, cwd: str | None = None) -> SandboxResult:
        """Execute a command in the sandbox."""
        safe, reason = self.check_command(command)
        if not safe:
            return SandboxResult(
                stdout="", stderr=f"BLOCKED: {reason}",
                exit_code=-1, blocked=True, block_reason=reason,
            )

        workdir = cwd or os.getcwd()
        if not self._is_path_allowed(workdir):
            return SandboxResult(
                stdout="", stderr=f"BLOCKED: path '{workdir}' not in allowlist",
                exit_code=-1, blocked=True,
                block_reason="Path not in allowlist",
            )

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self._timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return SandboxResult(
                    stdout="", stderr=f"TIMEOUT after {self._timeout}s",
                    exit_code=-1, timed_out=True,
                )

            return SandboxResult(
                stdout=stdout.decode()[: self._max_output],
                stderr=stderr.decode()[: self._max_output],
                exit_code=proc.returncode or 0,
            )
        except Exception as e:
            return SandboxResult(
                stdout="", stderr=f"Sandbox error: {e}",
                exit_code=-1,
            )

    async def execute_script(
        self,
        code: str,
        language: str = "python",
    ) -> SandboxResult:
        """Execute a code snippet in a temp file."""
        suffix = {"python": ".py", "javascript": ".js", "bash": ".sh"}.get(language, ".txt")
        runner = {
            "python": "python3",
            "javascript": "node",
            "bash": "bash",
        }.get(language, "cat")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, dir="/tmp"
        ) as f:
            f.write(code)
            f.flush()
            script_path = f.name

        try:
            result = await self.execute(f"{runner} {script_path}")
        finally:
            os.unlink(script_path)
        return result

    def _is_path_allowed(self, path: str) -> bool:
        abs_path = os.path.abspath(path)
        return any(abs_path.startswith(p) for p in self._allowed_paths)

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return OpenAI-format tool definitions."""
        return [
            {
                "name": "sandbox_execute",
                "description": "Execute a shell command in an isolated sandbox with safety checks",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command to execute"},
                        "cwd": {"type": "string", "description": "Working directory (optional)"},
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "sandbox_run_code",
                "description": "Run a code snippet in a sandboxed temp file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Source code to execute"},
                        "language": {
                            "type": "string",
                            "enum": ["python", "javascript", "bash"],
                            "description": "Programming language",
                        },
                    },
                    "required": ["code", "language"],
                },
            },
        ]
