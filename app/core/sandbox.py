"""Sandboxed code execution — secure subprocess isolation.

Provides:
- Restricted subprocess execution with resource limits
- Working directory isolation
- Network access control
- Output size limits
- Executable allowlist enforcement (SandboxConfig.allowed_commands)
- Blocked command patterns

Inspired by AutoGen's DockerCommandLineCodeExecutor and OpenInterpreter's sandbox.
"""

from __future__ import annotations

import asyncio
import os
import re
import resource
import shlex
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import ClassVar

import structlog

logger = structlog.get_logger()

# Characters that ``shlex`` splits out as standalone tokens when the tokenizer
# runs with ``punctuation_chars=True``. A token made up entirely of these is
# shell control flow, never a meaningful argv value.
_SHELL_CONTROL_CHARS = frozenset("();<>|&")

# ``VAR=value`` prefixes are consumed by a shell before the program name. This
# executor never runs a shell, so they are dropped rather than mistaken for the
# executable.
_ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# The default allowlist. Kept as a module constant so operators can extend it
# through the environment without a code change, and so tests can assert the
# shipped default explicitly.
_DEFAULT_ALLOWED_COMMANDS: tuple[str, ...] = (
    "python", "python3", "node", "npm", "npx",
    "cat", "ls", "head", "tail", "wc", "grep", "find",
    "echo", "pwd", "mkdir", "touch", "cp", "mv",
)

# Comma-separated additions to the default allowlist. This exists because the
# allowlist is now load-bearing: app/main.py constructs SandboxConfig() with no
# arguments, so without this an operator cannot widen the set at runtime.
_ALLOWED_COMMANDS_ENV = "CLIMBER_SANDBOX_ALLOWED_COMMANDS"


def _resolve_allowed_commands() -> list[str]:
    """Return the default allowlist plus any operator additions.

    ``CLIMBER_SANDBOX_ALLOWED_COMMANDS`` is additive and whitespace-tolerant, so
    a typo cannot silently empty the list. Only executables absent from the
    default are added; duplicates are dropped while preserving order.
    """
    resolved = list(_DEFAULT_ALLOWED_COMMANDS)
    raw = os.environ.get(_ALLOWED_COMMANDS_ENV, "")
    for candidate in (part.strip() for part in raw.split(",")):
        if not candidate:
            continue
        base = os.path.basename(candidate)
        if base and base not in resolved:
            resolved.append(base)
    return resolved


def _tokenize_command(command: str) -> list[str]:
    """Split a command string into shell-aware tokens.

    Unlike :func:`shlex.split`, ``punctuation_chars=True`` emits shell
    operators (``&&``, ``|``, ``;``, redirections, subshell parens) as their
    own tokens, which is what makes them detectable at all. Operators that
    appear inside quotes stay embedded in their word, matching what the
    executor would actually pass as an argument.

    Args:
        command: The raw command string.

    Returns:
        The token list.

    Raises:
        ValueError: If the command has unbalanced quotes.
    """
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    return list(lexer)


def _is_shell_control_token(token: str) -> bool:
    """Return True when a token is a bare shell operator.

    Args:
        token: A single token from :func:`_tokenize_command`.

    Returns:
        True for ``&&``, ``||``, ``;``, ``|``, ``&``, ``(``, ``)``, ``<``,
        ``>``, ``>>`` and similar, False for anything that could be an argv
        value.
    """
    return bool(token) and all(char in _SHELL_CONTROL_CHARS for char in token)


def _command_executables(command: str) -> tuple[list[str], str]:
    """Extract every executable a command string would launch.

    Args:
        command: The raw command string.

    Returns:
        A tuple of (executables, error). Exactly one side is meaningful: on
        success ``error`` is empty; on an ambiguous command ``executables`` is
        empty and ``error`` explains the refusal.
    """
    if not command.strip():
        return [], "Blocked: empty command"

    if "\n" in command or "\r" in command:
        return [], (
            "Blocked: multi-line command is ambiguous; the sandbox executes a "
            "single program with no shell, so only the first line would run"
        )

    try:
        tokens = _tokenize_command(command)
    except ValueError as exc:
        return [], f"Blocked: invalid shell syntax: {exc}"

    for token in tokens:
        if _is_shell_control_token(token):
            return [], (
                f"Blocked: compound command is not allowed; shell operator "
                f"'{token}' was found. The sandbox runs a single program with "
                f"no shell, so operators such as '&&', ';', '|' and "
                f"redirections cannot work. Issue one command per call."
            )
        if "`" in token:
            return [], (
                "Blocked: backtick command substitution is not allowed; the "
                "sandbox runs a single program with no shell, so the backticks "
                "would be passed through literally"
            )

    executables: list[str] = []
    expect_executable = True
    for token in tokens:
        if not expect_executable:
            continue
        if _ENV_ASSIGNMENT_RE.match(token):
            # Leading VAR=value prefix; a shell strips these before the
            # program name, so keep looking.
            continue
        executables.append(token)
        expect_executable = False

    if not executables:
        return [], "Blocked: command has no executable"

    return executables, ""


def _normalize_executable(name: str) -> str:
    """Reduce an executable reference to its comparable base name.

    ``/usr/bin/env``, ``./env`` and ``env`` all normalize to ``env`` so one
    allowlist entry covers every spelling.

    Args:
        name: The executable token as written in the command.

    Returns:
        The base name used for allowlist lookup.
    """
    return os.path.basename(name.strip())


@dataclass
class SandboxConfig:
    """Configuration for sandboxed execution."""
    workdir: str = ""
    timeout_seconds: int = 30
    max_output_bytes: int = 10000
    max_memory_mb: int = 256
    enable_network: bool = False
    allowed_commands: list[str] = field(default_factory=lambda: _resolve_allowed_commands())
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

    def _check_allowed_commands(self, command: str) -> tuple[bool, str]:
        """Check that every executable a command launches is allowlisted.

        Allowlist entries and command tokens are both reduced to base names
        before comparison, so one entry such as ``env`` covers ``env``,
        ``/usr/bin/env`` and ``./env``, and an entry written as an absolute
        path matches its own base name.

        Args:
            command: The raw command string.

        Returns:
            A tuple of (allowed, reason). An allowed command returns
            ``(True, "")``; a refusal names the executable and the configured
            allowlist.
        """
        executables, error = _command_executables(command)
        if error:
            return False, error

        allowed_names = {
            _normalize_executable(entry) for entry in self.config.allowed_commands
        }
        for executable in executables:
            base = _normalize_executable(executable)
            if base not in allowed_names:
                return False, (
                    f"Blocked: executable '{base}' is not in "
                    f"SandboxConfig.allowed_commands "
                    f"({sorted(allowed_names)})"
                )
        return True, ""

    def _is_command_safe(self, command: str, workdir: str) -> tuple[bool, str]:
        """Check if command passes safety rules.

        Args:
            command: The raw command string.
            workdir: The isolated working directory the command would run in.

        Returns:
            A tuple of (is_safe, reason). An unsafe command returns the
            blocking reason; a safe command returns ``(True, "")``.
        """
        allowed, reason = self._check_allowed_commands(command)
        if not allowed:
            return False, reason
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
        """Execute a command in the sandbox."""
        workdir = self._prepare_workdir()
        is_safe, reason = self._is_command_safe(command, workdir)
        if not is_safe:
            return f"BLOCKED: {reason}"

        effective_timeout = timeout if timeout is not None else self.config.timeout_seconds

        try:
            env = os.environ.copy()
            if not self.config.enable_network:
                # Stripping proxy variables does not stop a child process from
                # connecting directly, so the tool-level gate is what actually
                # enforces the policy. Keep this as defence in depth for
                # subprocesses that read a proxy from the environment.
                env.pop("HTTP_PROXY", None)
                env.pop("HTTPS_PROXY", None)
                env.pop("http_proxy", None)
                env.pop("https_proxy", None)

            args = shlex.split(command)
            if not args:
                return "BLOCKED: empty command"

            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
                env=env,
                preexec_fn=self._restrict_resources,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=effective_timeout,
                )
            except TimeoutError:
                proc.kill()
                await proc.wait()
                return f"TIMEOUT: Command exceeded {effective_timeout}s limit"

            return self._build_output(stdout, stderr, proc.returncode)

        except Exception as e:
            logger.exception("Sandbox execution error", error=str(e))
            return f"Error: {e!s}"

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
