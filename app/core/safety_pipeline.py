"""Safety Pipeline - unified three-layer security sandbox.

L1: Static Analysis (zero-cost pre-execution interception)
L2: Process Isolation (subprocess + resource limits)
L3: Container Isolation (Docker, high-risk operations)

Merges and replaces:
- security_sandbox.py (command blacklist, path whitelist, audit)
- sandbox.py (subprocess execution)
- mcp_plugins/sandbox_runtime.py (MCP plugin sandbox)
"""

from __future__ import annotations

import base64
import re
import urllib.parse
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


# --- Result Types -----------------------------------------------------

@dataclass
class SafetyResult:
    allowed: bool
    reason: str = ""
    risk_score: float = 0.0
    layer: str = ""

    @classmethod
    def pass_(cls, layer: str = "") -> SafetyResult:
        return cls(allowed=True, layer=layer)

    @classmethod
    def block(cls, reason: str, risk: float = 1.0, layer: str = "") -> SafetyResult:
        return cls(allowed=False, reason=reason, risk_score=risk, layer=layer)


@dataclass
class ExecutionResult:
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    timed_out: bool = False
    blocked: bool = False
    block_reason: str = ""
    error: str = ""


# --- Risk Level -------------------------------------------------------

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# --- L1: Static Analyzer ----------------------------------------------

class StaticAnalyzer:
    """Pre-execution static analysis - zero resource cost."""

    BLOCKED_COMMAND_PATTERNS = [
        # Destructive file operations
        r"rm\s+(-[rfRF]+\s+)+/",
        r"rm\s+-rf\s+~",
        r"shred\b",
        r"wipe\b",
        # Disk operations
        r"mkfs\b",
        r"fdisk\b",
        r"dd\s+if=.*\bof=/dev/",
        r">\s*/dev/sd[a-z]",
        # Fork bomb / DoS
        r":\(\)\s*{\s*:\s*\|\s*:\s*&\s*}\s*;",
        # Privilege escalation
        r"chmod\s+777\b",
        r"chown\s+-R\s+root\b",
        r"sudo\b",
        # Network threats
        r"nc\b.*-e\s+/bin/",
        r"bash\b.*-i\b.*>&\b",
        r"nohup\b.*&\s*$",
        r"curl\b.*\|\s*(sh|bash)\b",
        r"wget\b.*\|\s*(sh|bash)\b",
        # System control
        r"shutdown\b",
        r"reboot\b",
        r"poweroff\b",
        r"init\s+[06]\b",
        r"systemctl\s+(stop|disable)\b",
        r"kill\s+-9\s+1\b",
        # Code execution
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__",
        r"subprocess\.",
        r"os\.system\b",
        # Mount abuse
        r"mount\b.*-o\s+loop",
    ]

    BLOCKED_PATHS = [
        "/etc/shadow", "/etc/passwd", "/etc/sudoers",
        "/root/.ssh", "/home/*/.ssh",
        "/proc", "/sys", "/dev",
    ]

    def check_command(self, cmd: str) -> SafetyResult:
        """Check command safety with encoding bypass detection."""
        if not cmd or not cmd.strip():
            return SafetyResult.block("Empty command", layer="L1")

        decoded = self._try_decode(cmd)

        for pattern in self.BLOCKED_COMMAND_PATTERNS:
            if re.search(pattern, decoded, re.IGNORECASE):
                return SafetyResult.block(
                    f"Blocked pattern: {pattern}",
                    risk=1.0,
                    layer="L1",
                )

        if self._has_shell_injection(cmd):
            return SafetyResult.block(
                "Shell injection detected",
                risk=0.9,
                layer="L1",
            )

        return SafetyResult.pass_(layer="L1")

    def check_path(self, path: str, allowed_dirs: list[str]) -> SafetyResult:
        """Check path safety with traversal detection."""
        if not path:
            return SafetyResult.block("Empty path", layer="L1")

        try:
            abs_path = Path(path).resolve()
        except (OSError, ValueError) as e:
            return SafetyResult.block(f"Invalid path: {e}", layer="L1")

        for blocked in self.BLOCKED_PATHS:
            if "*" in blocked:
                import fnmatch
                if fnmatch.fnmatch(str(abs_path), blocked):
                    return SafetyResult.block(
                        f"Path matches blocked pattern: {blocked}",
                        risk=1.0,
                        layer="L1",
                    )
            elif str(abs_path) == blocked or str(abs_path).startswith(blocked + "/"):
                return SafetyResult.block(
                    f"Path is blocked: {blocked}",
                    risk=1.0,
                    layer="L1",
                )

        if allowed_dirs:
            is_allowed = False
            for allowed in allowed_dirs:
                try:
                    allowed_abs = Path(allowed).resolve()
                    if str(abs_path) == str(allowed_abs) or str(abs_path).startswith(str(allowed_abs) + "/"):
                        is_allowed = True
                        break
                except (OSError, ValueError):
                    continue
            if not is_allowed:
                return SafetyResult.block(
                    f"Path {abs_path} outside allowed dirs",
                    risk=0.8,
                    layer="L1",
                )

        return SafetyResult.pass_(layer="L1")

    def validate_schema(self, schema: dict, arguments: dict) -> SafetyResult:
        """Validate tool arguments against JSON Schema."""
        if not schema:
            return SafetyResult.pass_(layer="L1")

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for field_name in required:
            if field_name not in arguments:
                return SafetyResult.block(
                    f"Missing required field: {field_name}",
                    risk=0.3,
                    layer="L1",
                )

        for key, value in arguments.items():
            if key not in properties:
                continue
            prop = properties[key]
            expected = prop.get("type")
            if expected == "string" and not isinstance(value, str):
                return SafetyResult.block(f"Field {key} must be string", risk=0.2, layer="L1")
            if expected == "integer" and not isinstance(value, int):
                return SafetyResult.block(f"Field {key} must be integer", risk=0.2, layer="L1")
            if expected == "number" and not isinstance(value, (int, float)):
                return SafetyResult.block(f"Field {key} must be number", risk=0.2, layer="L1")
            if expected == "boolean" and not isinstance(value, bool):
                return SafetyResult.block(f"Field {key} must be boolean", risk=0.2, layer="L1")
            if expected == "array" and not isinstance(value, list):
                return SafetyResult.block(f"Field {key} must be array", risk=0.2, layer="L1")
            if expected == "object" and not isinstance(value, dict):
                return SafetyResult.block(f"Field {key} must be object", risk=0.2, layer="L1")

        return SafetyResult.pass_(layer="L1")

    def assess_risk(self, cmd: str) -> RiskLevel:
        """Assess risk level of a command."""
        result = self.check_command(cmd)
        if not result.allowed:
            if result.risk_score >= 0.9:
                return RiskLevel.CRITICAL
            if result.risk_score >= 0.6:
                return RiskLevel.HIGH
            return RiskLevel.MEDIUM

        decoded = self._try_decode(cmd)
        risky_patterns = [r"rm\b", r"git\s+push", r"DROP\b", r"DELETE\b", r"truncate\b"]
        for p in risky_patterns:
            if re.search(p, decoded, re.IGNORECASE):
                return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _try_decode(self, s: str) -> str:
        """Try to decode base64, hex, url-encoded strings."""
        try:
            decoded = base64.b64decode(s).decode("utf-8")
            if any(c in decoded for c in "rmcurlwgetbashsh "):
                return decoded
        except Exception as e:
            logger.warning("safety_pipeline.base64_decode", error=str(e))

        try:
            if len(s) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in s):
                decoded = bytes.fromhex(s).decode("utf-8")
                if any(c in decoded for c in "rmcurlwgetbashsh "):
                    return decoded
        except Exception as e:
            logger.warning("safety_pipeline.hex_decode", error=str(e))

        try:
            decoded = urllib.parse.unquote(s)
            if decoded != s and any(c in decoded for c in "rmcurlwgetbashsh "):
                return decoded
        except Exception as e:
            logger.warning("safety_pipeline.url_decode", error=str(e))

        return s

    def _has_shell_injection(self, cmd: str) -> bool:
        """Detect shell metacharacters that enable injection."""
        dangerous = [";", "&&", "||", "|", "$(", "`", ">", ">>"]
        in_single_quote = False
        in_double_quote = False
        i = 0
        while i < len(cmd):
            ch = cmd[i]
            if ch == "\\" and i + 1 < len(cmd):
                i += 2
                continue
            if ch == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif ch == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif not in_single_quote and not in_double_quote:
                for d in dangerous:
                    if cmd[i:i+len(d)] == d:
                        return True
            i += 1
        return False


# --- SafetyPipeline (统一入口) --------------------------------------

@dataclass
class SafetyConfig:
    workdir: str = "/workspace"
    allowed_paths: list[str] = field(default_factory=list)
    timeout_seconds: int = 30
    max_output_bytes: int = 10000
    max_memory_mb: int = 256
    enable_network: bool = False
    use_docker: bool = False
    docker_image: str = "python:3.11-slim"


class SafetyPipeline:
    """Three-layer safety pipeline - single entry point."""

    def __init__(self, config: SafetyConfig | None = None):
        self.config = config or SafetyConfig()
        self.l1 = StaticAnalyzer()
        self._l2 = None
        self._l3 = None

    @property
    def l2(self):
        if self._l2 is None:
            from app.core.sandbox import SandboxConfig, SandboxExecutor
            self._l2 = SandboxExecutor(SandboxConfig(
                workdir=self.config.workdir,
                timeout_seconds=self.config.timeout_seconds,
                max_output_bytes=self.config.max_output_bytes,
                max_memory_mb=self.config.max_memory_mb,
                enable_network=self.config.enable_network,
            ))
        return self._l2

    @property
    def l3(self):
        if self._l3 is None:
            from app.core.docker_sandbox import DockerSandbox, DockerSandboxConfig
            self._l3 = DockerSandbox(DockerSandboxConfig(
                image=self.config.docker_image,
                timeout_seconds=self.config.timeout_seconds,
                max_output_bytes=self.config.max_output_bytes,
            ))
        return self._l3

    async def validate_and_execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ExecutionResult:
        # L1: Static analysis
        l1_result = self._l1_check(tool_name, arguments)
        if not l1_result.allowed:
            logger.warning("safety_l1_blocked", tool=tool_name, reason=l1_result.reason)
            return ExecutionResult(error=f"BLOCKED (L1): {l1_result.reason}", returncode=-1, blocked=True, block_reason=l1_result.reason)

        risk = self._assess_risk(tool_name, arguments)

        if risk in (RiskLevel.HIGH, RiskLevel.CRITICAL) and self.config.use_docker:
            return await self._l3_execute(tool_name, arguments)

        return await self._l2_execute(tool_name, arguments)

    def _l1_check(self, tool_name: str, arguments: dict[str, Any]) -> SafetyResult:
        if "command" in arguments:
            result = self.l1.check_command(arguments["command"])
            if not result.allowed:
                return result
        if "path" in arguments:
            allowed = [self.config.workdir, *self.config.allowed_paths]
            result = self.l1.check_path(arguments["path"], allowed)
            if not result.allowed:
                return result
        return SafetyResult.pass_(layer="L1")

    def _assess_risk(self, tool_name: str, arguments: dict[str, Any]) -> RiskLevel:
        if "command" in arguments:
            return self.l1.assess_risk(arguments["command"])
        high_risk_tools = {"run_command", "write_file", "delete_file", "bash", "shell"}
        if tool_name in high_risk_tools:
            return RiskLevel.HIGH
        return RiskLevel.LOW

    async def _l2_execute(self, tool_name: str, arguments: dict[str, Any]) -> ExecutionResult:
        if tool_name == "run_command" and "command" in arguments:
            output = await self.l2.execute(arguments["command"])
            return ExecutionResult(stdout=output, returncode=0 if "BLOCKED" not in output and "Error" not in output else -1)
        return ExecutionResult(stdout="", returncode=0, error="L2 passthrough")

    async def _l3_execute(self, tool_name: str, arguments: dict[str, Any]) -> ExecutionResult:
        if tool_name == "run_command" and "command" in arguments:
            import shlex
            try:
                cmd = shlex.split(arguments["command"])
            except ValueError:
                return ExecutionResult(error="Invalid command syntax", returncode=-1)
            return await self.l3.execute(cmd, self.config.workdir)
        return ExecutionResult(stdout="", returncode=0, error="L3 passthrough")

    def check_only(self, tool_name: str, arguments: dict[str, Any]) -> SafetyResult:
        return self._l1_check(tool_name, arguments)


_safety_pipeline: SafetyPipeline | None = None


def get_safety_pipeline(config: SafetyConfig | None = None) -> SafetyPipeline:
    global _safety_pipeline
    if _safety_pipeline is None:
        _safety_pipeline = SafetyPipeline(config)
    return _safety_pipeline
