"""Security Sandbox + Audit System.

Implements:
1. Command sandbox: path whitelist, hazard command blacklist, resource limits
2. File system isolation: project directory isolation, no cross-directory access
3. Full operation audit: all file mods, commands, API calls logged with traceability
4. Permission approval workflow: pause → request → temporary grant → revoke
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger()


# ─── Execution Mode ──────────────────────────────────────────────────────────

class ExecutionMode(Enum):
    SANDBOX = "sandbox"          # Isolated window, restricted access
    FULL_AUTO = "full_auto"      # Full local access with permission grants


class ExecutionMode(Enum):
    SANDBOX = "sandbox"          # Isolated window, restricted access
    FULL_AUTO = "full_auto"      # Full local access with permission grants


class AgentMode(Enum):
    PLAN = "plan"                # Read-only preview mode
    ACT = "act"                  # Real execution mode


class PermissionLevel(Enum):
    DENY = "deny"                # Forbidden
    ASK = "ask"                  # Ask user
    ALLOW = "allow"              # Directly allowed


@dataclass
class PermissionRule:
    action: str                  # read / write / execute / delete
    resource_pattern: str        # glob pattern
    level: PermissionLevel
    description: str = ""


class PermissionOverlay:
    """Three-layer permission overlay: defaults → agent-level → user-level.

    """

    def __init__(self):
        self._defaults: list[PermissionRule] = []
        self._agent_overrides: dict[str, list[PermissionRule]] = {}
        self._user_overrides: dict[str, list[PermissionRule]] = {}

    def set_defaults(self, rules: list[PermissionRule]) -> None:
        self._defaults = rules

    def set_agent_rules(self, agent_id: str, rules: list[PermissionRule]) -> None:
        self._agent_overrides[agent_id] = rules

    def set_user_rules(self, user_id: str, rules: list[PermissionRule]) -> None:
        self._user_overrides[user_id] = rules

    def evaluate(self, action: str, resource: str, agent_id: str | None = None, user_id: str | None = None) -> PermissionLevel:
        """Evaluate permission with three-layer overlay."""
        effective = self._merge_rules(action, resource, agent_id, user_id)
        if not effective:
            return PermissionLevel.DENY
        return effective.level

    def _merge_rules(self, action: str, resource: str, agent_id: str | None, user_id: str | None) -> PermissionRule | None:
        merged: dict[str, PermissionRule] = {}
        for rule in self._defaults:
            if rule.action == action and self._match(rule.resource_pattern, resource):
                merged[rule.resource_pattern] = rule
        if agent_id and agent_id in self._agent_overrides:
            for rule in self._agent_overrides[agent_id]:
                if rule.action == action and self._match(rule.resource_pattern, resource):
                    merged[rule.resource_pattern] = rule
        if user_id and user_id in self._user_overrides:
            for rule in self._user_overrides[user_id]:
                if rule.action == action and self._match(rule.resource_pattern, resource):
                    merged[rule.resource_pattern] = rule
        if not merged:
            return None
        best = max(merged.items(), key=lambda x: self._priority(x[1].level))
        return best[1]

    @staticmethod
    def _match(pattern: str, path: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(path, pattern)

    @staticmethod
    def _priority(level: PermissionLevel) -> int:
        return {PermissionLevel.DENY: 0, PermissionLevel.ASK: 1, PermissionLevel.ALLOW: 2}.get(level, 0)


# ─── JSON Schema Validation ──────────────────────────────────────────────────

class SchemaValidationError(Exception):
    """Raised when tool input fails JSON Schema validation."""


def validate_tool_input(schema: dict[str, Any], arguments: dict[str, Any]) -> None:
    """Validate tool arguments against JSON Schema.

    """
    if not schema:
        return
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    for field_name in required:
        if field_name not in arguments:
            raise SchemaValidationError(f"Missing required field: {field_name}")
    for key, value in arguments.items():
        if key not in properties:
            continue
        prop = properties[key]
        expected = prop.get("type")
        if expected == "string" and not isinstance(value, str):
            raise SchemaValidationError(f"Field '{key}' must be a string")
        elif expected == "integer" and not isinstance(value, int):
            raise SchemaValidationError(f"Field '{key}' must be an integer")
        elif expected == "number" and not isinstance(value, (int, float)):
            raise SchemaValidationError(f"Field '{key}' must be a number")
        elif expected == "boolean" and not isinstance(value, bool):
            raise SchemaValidationError(f"Field '{key}' must be a boolean")
        elif expected == "array" and not isinstance(value, list):
            raise SchemaValidationError(f"Field '{key}' must be an array")
        elif expected == "object" and not isinstance(value, dict):
            raise SchemaValidationError(f"Field '{key}' must be an object")


# ─── Command Blacklist ──────────────────────────────────────────────────────

HAZARD_COMMANDS = [
    # Destructive file operations
    r'\brm\s+(-[rfRF]+\s+)?/\b',
    r'\brm\s+-rf\s+/\b',
    r'\bshred\b',
    r'\bwipe\b',
    # Disk operations
    r'\bmkfs\b',
    r'\bfdisk\b',
    r'\bdd\b.*\bof=/dev/',
    r'>\s*/dev/sd[a-z]',
    # Fork bomb / DoS
    r':\(\)\s*{\s*:\s*\|\s*:\s*&\s*}\s*;',
    # Privilege escalation
    r'\bchmod\s+777\b',
    r'\bchown\s+-R\s+root\b',
    r'\bsudo\b.*\brm\b',
    # Network threats
    r'\bnc\b.*-e\s+/bin/',
    r'\bbash\b.*-i\b.*>&\b',
    r'\bnohup\b.*&\s*$',
    r'\bcurl\b.*\|\s*(sh|bash)\b',
    r'\bwget\b.*\|\s*(sh|bash)\b',
    # System control
    r'\bshutdown\b',
    r'\breboot\b',
    r'\bpoweroff\b',
    r'\binit\s+[06]\b',
    r'\bsystemctl\s+(stop|disable)\b',
    # Mount abuse
    r'\bmount\b.*-o\s+loop',
]


# ─── Security Sandbox ──────────────────────────────────────────────────────

@dataclass
class SandboxConfig:
    """Sandbox isolation configuration."""
    workdir: str                    # Isolated working directory
    allowed_paths: list[str] = field(default_factory=list)  # Additional allowed paths
    blocked_paths: list[str] = field(default_factory=lambda: [
        '/etc/shadow', '/etc/passwd', '/etc/sudoers',
        '/root/.ssh', '/home/*/.ssh',
        '/proc', '/sys', '/dev',
    ])
    max_file_size_mb: int = 50
    max_output_size_kb: int = 500
    command_timeout_seconds: int = 120
    enable_network: bool = False


class SecuritySandbox:
    """Local process sandbox for safe code execution.

    Features:
    - File access isolation (project directory only by default)
    - Command hazard detection
    - Resource limits (file size, output size, timeout)
    - Audit logging for all operations
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig(workdir="/tmp/sandbox")
        self._active = True

    def validate_file_access(self, path: str, mode: str = 'read') -> tuple[bool, str]:
        """Validate if a file can be accessed."""
        abs_path = os.path.abspath(path)

        # Check blocked paths
        for blocked in self.config.blocked_paths:
            if abs_path.startswith(blocked) or abs_path == blocked:
                return False, f"Access denied: path '{abs_path}' is in blocked list"

        # Check allowed paths
        allowed = [self.config.workdir] + self.config.allowed_paths
        is_allowed = any(abs_path.startswith(p) for p in allowed)

        if not is_allowed:
            return False, f"Access denied: path '{abs_path}' is outside allowed directories"

        # Check file size for reads
        if mode == 'read' and os.path.exists(abs_path):
            size_mb = os.path.getsize(abs_path) / (1024 * 1024)
            if size_mb > self.config.max_file_size_mb:
                return False, f"File too large: {size_mb:.1f}MB (max {self.config.max_file_size_mb}MB)"

        return True, "OK"

    def validate_command(self, command: str) -> tuple[bool, str]:
        """Validate a shell command against hazard list."""
        for pattern in HAZARD_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Command blocked by safety policy: matches hazard pattern '{pattern}'"
        return True, "OK"


# Allowed commands for the allowlist check
_ALLOWED_COMMANDS = {
    "ls", "cat", "echo", "pwd", "cd", "mkdir", "cp", "mv", "rm",
    "touch", "head", "tail", "grep", "find", "wc", "sort", "uniq",
    "diff", "file", "which", "env", "export", "python3", "python",
    "pip", "pip3", "node", "npm", "npx", "git", "curl", "wget",
    "tar", "zip", "unzip", "chmod", "chown", "ln", "tee", "awk",
    "sed", "xargs", "jq", "yq", "make", "pytest", "go", "rustc",
    "cargo", "java", "javac", "mvn", "gradle", "docker",
}


def validate_command_allowlist(command: str) -> tuple[bool, str]:
    """Validate that a command base name is in the allowed commands list."""
    parts = command.strip().split()
    if not parts:
        return False, "Empty command"
    base = parts[0].lstrip("./")
    base = os.path.basename(base)
    if base not in _ALLOWED_COMMANDS:
        return False, f"Command '{base}' is not in the allowed commands list"
    return True, "OK"

    def sanitize_output(self, output: str) -> str:
        """Truncate oversized output."""
        max_bytes = self.config.max_output_size_kb * 1024
        if len(output.encode('utf-8')) > max_bytes:
            truncated = output.encode('utf-8')[:max_bytes].decode('utf-8', errors='ignore')
            return truncated + f"\n... [Output truncated: exceeded {self.config.max_output_size_kb}KB limit]"
        return output


# ─── Code Execution Sandbox ──────────────────────────────────────────────────

class VerificationResult:
    def __init__(self, allowed: bool, reason: str = ""):
        self.allowed = allowed
        self.reason = reason


class CodeSandbox:
    """AST-level static code analysis sandbox.

    """

    FORBIDDEN_MODULES = {"os", "sys", "subprocess", "socket", "shutil", "pickle", "marshal", "ctypes", "signal", "pty", "fcntl"}
    FORBIDDEN_FUNCTIONS = {"eval", "exec", "open", "getattr", "setattr", "delattr", "globals", "locals", "compile", "__import__"}
    FORBIDDEN_DUNDER = {"__dict__", "__class__", "__bases__", "__subclasses__", "__init_subclass__", "__setattr__", "__delattr__"}

    def verify(self, code: str) -> VerificationResult:
        """Verify code safety using AST analysis."""
        try:
            import ast
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        if top in self.FORBIDDEN_MODULES:
                            return VerificationResult(allowed=False, reason=f"Forbidden module: {top}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        top = node.module.split(".")[0]
                        if top in self.FORBIDDEN_MODULES:
                            return VerificationResult(allowed=False, reason=f"Forbidden module: {top}")
                elif isinstance(node, ast.Attribute):
                    if node.attr in self.FORBIDDEN_DUNDER:
                        return VerificationResult(allowed=False, reason=f"Forbidden dunder: {node.attr}")
                elif isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name) and func.id in self.FORBIDDEN_FUNCTIONS:
                        return VerificationResult(allowed=False, reason=f"Forbidden function: {func.id}")
            return VerificationResult(allowed=True)
        except SyntaxError as e:
            return VerificationResult(allowed=False, reason=f"Syntax error: {e}")


# ─── Permission Approval System ────────────────────────────────────────────

class ApprovalStatus(Enum):
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"
    EXPIRED = "expired"


@dataclass
class PermissionRequest:
    id: str
    session_id: str
    action: str              # e.g., "access_path", "run_command"
    details: str             # Human-readable description
    risk_level: str          # "low" | "medium" | "high"
    requested_at: float
    status: ApprovalStatus = ApprovalStatus.PENDING
    resolved_at: float | None = None
    temporary: bool = True   # Auto-revoke after use


class PermissionApprovalSystem:
    """Manages permission escalation requests.

    When Agent needs to exceed its current permission level:
    1. Pause current task
    2. Send approval request to user (desktop + mobile)
    3. User grants/denies
    4. If granted: temporarily elevate permission, execute, then revoke
    """

    def __init__(self):
        self._requests: dict[str, PermissionRequest] = {}
        self._active_grants: dict[str, list[str]] = {}  # session_id -> [granted_actions]

    def request_permission(
        self,
        session_id: str,
        action: str,
        details: str,
        risk_level: str = "medium",
    ) -> PermissionRequest:
        """Create a permission request."""
        req = PermissionRequest(
            id=str(uuid4()),
            session_id=session_id,
            action=action,
            details=details,
            risk_level=risk_level,
            requested_at=time.time(),
        )
        self._requests[req.id] = req
        logger.info("permission_requested", session_id=session_id, action=action, risk=risk_level)
        return req

    def grant_permission(self, request_id: str, temporary: bool = True) -> PermissionRequest | None:
        """Grant a permission request."""
        req = self._requests.get(request_id)
        if not req:
            return None

        req.status = ApprovalStatus.GRANTED
        req.resolved_at = time.time()
        req.temporary = temporary

        # Track active grant
        if req.session_id not in self._active_grants:
            self._active_grants[req.session_id] = []
        self._active_grants[req.session_id].append(req.action)

        logger.info("permission_granted", request_id=request_id, action=req.action)
        return req

    def deny_permission(self, request_id: str) -> PermissionRequest | None:
        """Deny a permission request."""
        req = self._requests.get(request_id)
        if not req:
            return None

        req.status = ApprovalStatus.DENIED
        req.resolved_at = time.time()

        logger.info("permission_denied", request_id=request_id, action=req.action)
        return req

    def check_permission(self, session_id: str, action: str) -> bool:
        """Check if a session has an active permission grant."""
        grants = self._active_grants.get(session_id, [])
        return action in grants

    def revoke_permission(self, session_id: str, action: str):
        """Revoke a temporary permission grant."""
        grants = self._active_grants.get(session_id, [])
        if action in grants:
            grants.remove(action)
            logger.info("permission_revoked", session_id=session_id, action=action)

    def get_pending_requests(self, session_id: str | None = None) -> list[PermissionRequest]:
        """Get pending approval requests."""
        requests = [r for r in self._requests.values() if r.status == ApprovalStatus.PENDING]
        if session_id:
            requests = [r for r in requests if r.session_id == session_id]
        return requests

    def clear_session(self, session_id: str):
        """Clear all permissions for a session."""
        self._active_grants.pop(session_id, None)


# ─── Audit Log System ──────────────────────────────────────────────────────

@dataclass
class AuditEntry:
    id: str
    session_id: str
    timestamp: float
    action: str
    severity: str  # "info" | "warning" | "critical"
    details: dict[str, Any]
    result: str = ""


class AuditSystem:
    """Full operation audit trail.

    Logs every:
    - File modification (before/after diff)
    - Command execution (full command + output preview)
    - API call (endpoint, status, duration)
    - Permission escalation (request, grant, deny)

    Persists to database for long-term storage.
    """

    def __init__(self):
        self._entries: list[AuditEntry] = []

    def log_file_operation(
        self,
        session_id: str,
        operation: str,  # read, write, delete, modify
        path: str,
        details: dict[str, Any] | None = None,
        user_id: str | None = None,
    ):
        """Log a file operation."""
        severity = "critical" if operation in ("delete", "modify") else "info"
        self._entries.append(AuditEntry(
            id=str(uuid4()),
            session_id=session_id,
            timestamp=time.time(),
            action=f"file:{operation}",
            severity=severity,
            details={"path": path, **(details or {})},
        ))
        asyncio.create_task(self._persist(
            session_id=session_id, action=f"file:{operation}", severity=severity,
            details={"path": path, **(details or {})}, user_id=user_id,
        ))

    def log_command(
        self,
        session_id: str,
        command: str,
        result: str = "",
        blocked: bool = False,
        user_id: str | None = None,
    ):
        """Log a command execution."""
        self._entries.append(AuditEntry(
            id=str(uuid4()),
            session_id=session_id,
            timestamp=time.time(),
            action="command:execute",
            severity="critical" if blocked else "warning",
            details={"command": command, "blocked": blocked, "output_preview": result[:200]},
            result=result,
        ))
        asyncio.create_task(self._persist(
            session_id=session_id, action="command:execute",
            severity="critical" if blocked else "warning",
            details={"command": command, "blocked": blocked, "output_preview": result[:200]},
            result=result, user_id=user_id,
        ))

    def log_api_call(
        self,
        session_id: str,
        endpoint: str,
        status_code: int,
        duration_ms: float,
        user_id: str | None = None,
    ):
        """Log an API call."""
        self._entries.append(AuditEntry(
            id=str(uuid4()),
            session_id=session_id,
            timestamp=time.time(),
            action="api:call",
            severity="warning" if status_code >= 400 else "info",
            details={"endpoint": endpoint, "status": status_code, "duration_ms": duration_ms},
        ))
        asyncio.create_task(self._persist(
            session_id=session_id, action="api:call",
            severity="warning" if status_code >= 400 else "info",
            details={"endpoint": endpoint, "status": status_code, "duration_ms": duration_ms},
            user_id=user_id,
        ))

    def log_permission(
        self,
        session_id: str,
        action: str,
        granted: bool,
        reason: str = "",
        user_id: str | None = None,
    ):
        """Log a permission event."""
        self._entries.append(AuditEntry(
            id=str(uuid4()),
            session_id=session_id,
            timestamp=time.time(),
            action=f"permission:{action}",
            severity="warning" if granted else "info",
            details={"granted": granted, "reason": reason},
        ))
        asyncio.create_task(self._persist(
            session_id=session_id, action=f"permission:{action}",
            severity="warning" if granted else "info",
            details={"granted": granted, "reason": reason}, user_id=user_id,
        ))

    async def _persist(self, session_id: str, action: str, severity: str, details: dict[str, Any], result: str = "", user_id: str | None = None) -> None:
        """Persist audit entry to database."""
        try:
            from app.storage.models_memory import AuditLog
            from app.storage import async_session
            async with async_session() as db:
                log = AuditLog(
                    session_id=session_id,
                    user_id=user_id,
                    action=action,
                    severity=severity,
                    details=details,
                    result=result,
                )
                db.add(log)
                await db.commit()
        except Exception as e:
            logger.warning("security_sandbox.audit_log_failed", error=str(e))

    def get_entries(
        self,
        session_id: str | None = None,
        severity: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Get audit entries with optional filtering."""
        entries = self._entries
        if session_id:
            entries = [e for e in entries if e.session_id == session_id]
        if severity:
            entries = [e for e in entries if e.severity == severity]
        return sorted(entries, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_recent_critical(self, limit: int = 20) -> list[AuditEntry]:
        """Get recent critical entries."""
        return [e for e in self._entries if e.severity == "critical"][-limit:]


# ─── Singleton Instances ────────────────────────────────────────────────────

security_sandbox = SecuritySandbox()
permission_system = PermissionApprovalSystem()
audit_system = AuditSystem()
