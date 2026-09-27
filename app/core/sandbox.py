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
import signal
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import ClassVar

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

    # Sensitive paths that should never be accessed
    SENSITIVE_PATHS: ClassVar[tuple[str, ...]] = (
        "/etc/shadow", "/etc/passwd", "/etc/sudoers",
        "/etc/ssh/", "/root/.ssh/", "/etc/ssl/private/",
    )

    def _is_command_safe(self, command: str, workdir: str) -> tuple[bool, str]:
        """Check if command passes safety rules."""
        for pattern in self.config.blocked_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Blocked by security rule: pattern '{pattern}'"
        # Check for sensitive file access by path traversal
        real_workdir = os.path.realpath(workdir)
        if re.search(r"(?:^|[\s;|&])\.\.(?:/|\\)", command):
            return False, "Blocked: parent-directory traversal is not allowed"
        for token in re.findall(r"(?:^|\s|;|\|)(?:/[\w./-]+|~[\w/.-]*)", command):
            candidate = os.path.expanduser(os.path.expandvars(token.strip()))
            candidate = os.path.realpath(candidate)
            if candidate.startswith(real_workdir + os.sep) or candidate == real_workdir:
                continue
            for sensitive in self.SENSITIVE_PATHS:
                if candidate == sensitive or candidate.startswith(sensitive + os.sep):
                    return False, f"Blocked: access to sensitive path '{sensitive}'"
            if candidate.startswith("/"):
                return False, f"Blocked: path '{candidate}' escapes workdir"
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

    async def execute(self, command: str, timeout: int | None = None) -> str:
        """Execute a command in the sandbox via ``bash -c``.

        Shell mode is required for real agent usability: pipes, ``&&``,
        redirects, and command substitution are how models compose
        commands. Safety checks run on the full command string before
        execution.
        """
        workdir = self._prepare_workdir()
        is_safe, reason = self._is_command_safe(command, workdir)
        if not is_safe:
            return f"BLOCKED: {reason}"

        effective_timeout = timeout if timeout is not None else self.config.timeout_seconds

        try:
            env = self._build_env()

            proc = await asyncio.create_subprocess_exec(
                "bash", "-c", command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
                env=env,
                preexec_fn=self._restrict_resources,
                start_new_session=True,
            )

            stdout, stderr, returncode, timed_out = await self._communicate(proc, effective_timeout)
            output = self._build_output(stdout, stderr, returncode)
            if timed_out:
                prefix = f"TIMEOUT: Command exceeded {effective_timeout}s limit."
                return f"{prefix}\n{output}" if output else prefix
            return output

        except Exception as e:
            logger.error("Sandbox execution error", error=str(e))
            return f"Error: {e!s}"

    async def _communicate(
        self, proc: asyncio.subprocess.Process, timeout: float
    ) -> tuple[bytes, bytes, int, bool]:
        """Drain stdout/stderr incrementally; on timeout kill the process
        group and return whatever output was collected so far."""
        out_chunks: list[bytes] = []
        err_chunks: list[bytes] = []
        drain_out = asyncio.ensure_future(self._drain(proc.stdout, out_chunks))
        drain_err = asyncio.ensure_future(self._drain(proc.stderr, err_chunks))
        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout)
            await asyncio.gather(drain_out, drain_err)
            return b"".join(out_chunks), b"".join(err_chunks), proc.returncode or 0, False
        except TimeoutError:
            self._kill_process_group(proc)
            await proc.wait()
            drain_out.cancel()
            drain_err.cancel()
            await asyncio.gather(drain_out, drain_err, return_exceptions=True)
            return b"".join(out_chunks), b"".join(err_chunks), -1, True

    @staticmethod
    async def _drain(stream: asyncio.StreamReader | None, chunks: list[bytes]) -> None:
        if stream is None:
            return
        while True:
            chunk = await stream.read(65536)
            if not chunk:
                break
            chunks.append(chunk)

    def _build_env(self) -> dict[str, str]:
        """Build the child environment: network policy + output taming."""
        env = os.environ.copy()
        if not self.config.enable_network:
            for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
                env.pop(var, None)
        # Disable pagers and progress bars so they cannot pollute output
        # or block on interactivity (learned from mini-SWE-agent).
        env.setdefault("PAGER", "cat")
        env.setdefault("MANPAGER", "cat")
        env.setdefault("GIT_PAGER", "cat")
        env.setdefault("LESS", "-R")
        env.setdefault("PIP_PROGRESS_BAR", "off")
        env.setdefault("TQDM_DISABLE", "1")
        return env

    @staticmethod
    def _kill_process_group(proc: asyncio.subprocess.Process) -> None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except ProcessLookupError:
                pass

    def _build_output(self, stdout: bytes, stderr: bytes, returncode: int) -> str:
        parts: list[str] = []
        stdout_text = stdout.decode("utf-8", errors="replace").rstrip()
        if stdout_text:
            parts.append(stdout_text)
        stderr_text = stderr.decode("utf-8", errors="replace").rstrip()
        if stderr_text:
            parts.append(f"[stderr]: {stderr_text}")
        if returncode != 0:
            parts.append(f"[exit code: {returncode}]")
        full_output = "\n".join(parts)
        max_bytes = self.config.max_output_bytes
        if len(full_output.encode()) > max_bytes:
            # Keep head + tail (the regions the model reasons over) and
            # report exactly how much was elided.
            head_chars = int(max_bytes * 0.6)
            tail_chars = max_bytes - head_chars
            elided = len(full_output) - head_chars - tail_chars
            full_output = (
                full_output[:head_chars]
                + f"\n\n[Output truncated: {elided} characters elided. "
                "Re-run with a narrower command (head/tail/sed/grep) or "
                "redirect full output to a file and search it.]\n\n"
                + full_output[-tail_chars:]
            )
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
