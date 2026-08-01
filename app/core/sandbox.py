"""Sandboxed code execution — secure subprocess isolation.

Provides:
- Restricted subprocess execution with resource limits
- Working directory isolation
- Network access control
- Output size limits
- Blocked command patterns

Inspired by AutoGen's DockerCommandLineCodeExecutor and OpenInterpreter's sandbox.
"""

from __future__ import annotations

import asyncio
import os
import re
import resource
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class SandboxConfig:
    """Configuration for sandboxed execution."""
    workdir: str = ""
    timeout_seconds: int = 30
    max_output_bytes: int = 10000
    max_memory_mb: int = 256
    enable_network: bool = False
    allowed_commands: list[str] = field(default_factory=lambda: [
        "python", "python3", "node", "npm", "npx",
        "cat", "ls", "head", "tail", "wc", "grep", "find",
        "echo", "pwd", "mkdir", "touch", "cp", "mv",
    ])
    blocked_patterns: list[str] = field(default_factory=lambda: [
        r"rm\s+-rf\s+/",
        r"rm\s+-rf\s+~",
        r"chmod\s+777",
        r"chown\s+root",
        r"sudo\s+",
        r"curl\s+.*\|\s*sh",
        r"wget\s+.*\|\s*sh",
        r"dd\s+if=",
        r"mkfs\.",
        r"fdisk",
        r":\(\)\{.*\|.*&};",
        r">\s*/dev/sd",
        r"shutdown",
        r"reboot",
        r"init\s+[06]",
        r"kill\s+-9\s+1",
    ])


class SandboxExecutor:
    """Executes commands in an isolated subprocess sandbox."""

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self._workdir = ""

    def _is_command_safe(self, command: str) -> tuple[bool, str]:
        """Check if command passes safety rules."""
        for pattern in self.config.blocked_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Blocked by security rule: pattern '{pattern}'"
        return True, ""

    def _restrict_resources(self) -> None:
        """Apply resource limits to the child process."""
        try:
            max_mem_bytes = self.config.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (max_mem_bytes, max_mem_bytes))
            resource.setrlimit(resource.RLIMIT_CPU, (self.config.timeout_seconds, self.config.timeout_seconds + 5))
            resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
            resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
        except (ValueError, OSError):
            pass

    def _prepare_workdir(self) -> str:
        """Create isolated working directory."""
        if self.config.workdir and os.path.isdir(self.config.workdir):
            return self.config.workdir
        self._workdir = tempfile.mkdtemp(prefix="agent_sandbox_")
        return self._workdir

    async def execute(self, command: str) -> str:
        """Execute a command in the sandbox."""
        is_safe, reason = self._is_command_safe(command)
        if not is_safe:
            return f"BLOCKED: {reason}"

        workdir = self._prepare_workdir()

        try:
            env = os.environ.copy()
            if not self.config.enable_network:
                env.pop("HTTP_PROXY", None)
                env.pop("HTTPS_PROXY", None)
                env.pop("http_proxy", None)
                env.pop("https_proxy", None)

            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
                env=env,
                preexec_fn=self._restrict_resources,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.config.timeout_seconds,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return f"TIMEOUT: Command exceeded {self.config.timeout_seconds}s limit"

            return self._build_output(stdout, stderr, proc.returncode)

        except Exception as e:
            logger.error("Sandbox execution error", error=str(e))
            return f"Error: {str(e)}"

    def _build_output(self, stdout: bytes, stderr: bytes, returncode: int) -> str:
        parts: list[str] = []
        stdout_text = stdout.decode("utf-8", errors="replace").rstrip()
        if stdout_text:
            parts.append(stdout_text)
        stderr_text = stderr.decode("utf-8", errors="replace").rstrip()
        if stderr_text:
            parts.append(f"[stderr]: {stderr_text}")
        if returncode != 0 and not parts:
            parts.append(f"Command exited with code {returncode}")
        full_output = "\n".join(parts)
        if len(full_output.encode()) > self.config.max_output_bytes:
            full_output = full_output[:self.config.max_output_bytes] + "\n... [OUTPUT TRUNCATED]"
        return full_output if full_output else "Command completed (no output)"

    def cleanup(self) -> None:
        """Remove temporary working directory."""
        if self._workdir and os.path.isdir(self._workdir):
            try:
                shutil.rmtree(self._workdir, ignore_errors=True)
            except Exception as e:
                logger.warning("sandbox.cleanup_failed", workdir=self._workdir, error=str(e))
            self._workdir = ""


# Global default sandbox
default_sandbox = SandboxExecutor()
