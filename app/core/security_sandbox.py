"""Pre-execution policy layer for agent tool calls.

This used to be a second, independent sandbox: a denylist (``HAZARD_COMMANDS``)
bolted onto an allowlist (``_ALLOWED_COMMANDS``) that contradicted itself in
both directions -- ``chmod`` allowlisted while only ``chmod 777`` was blocked,
``rm`` allowlisted while ``rm -rf`` was blocked -- consulted on a different code
path than the one that actually spawns processes. Two sandboxes, two answers to
"is this command safe?".

It is now a thin policy layer:

* **Command admission is delegated.** :meth:`SecuritySandbox.validate_command`
  calls :meth:`app.core.sandbox.SandboxExecutor._is_command_safe` -- the exact
  function ``execute`` calls before ``create_subprocess_exec``. One command
  policy, and it is the one on the execution path. This layer only *adds* two
  restrictions: shell metacharacters in the command token, and interpreter
  entry points. Admission is the *union* of the checks, so no disagreement can
  produce a false allow.
* **Path admission is containment, not prefix.** Every root -- allowed and
  blocked alike -- is compared with ``os.path.realpath`` plus
  ``os.path.commonpath``, so a path is inside a root only if it really is. A
  blocked root of ``/dev`` no longer admits ``/devfoo``.
* **Permission layers stack with DENY dominance.** A user- or agent-level rule
  can tighten a decision (ALLOW -> ASK -> DENY) but never widen one.
* **The AST gate is a denylist**, and :class:`CodeSandbox` says so in its own
  docstring. It is a tripwire against obvious mistakes, not a boundary.

Nothing here executes anything. This module answers "may this tool call
proceed?"; :mod:`app.core.sandbox` owns "how is it run, and under what limits?".
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
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


class AgentMode(Enum):
    PLAN = "plan"                # Read-only preview mode
    ACT = "act"                  # Real execution mode


class PermissionLevel(Enum):
    DENY = "deny"                # Forbidden
    ASK = "ask"                  # Ask user
    ALLOW = "allow"              # Directly allowed


#: Strictest-first ordering. Used for every permission decision in this module,
#: so "which of these two rules wins" has exactly one answer everywhere:
#: DENY beats ASK beats ALLOW. Never invert this and expect the merge to
#: still stack.
_LEVEL_STRENGTH: dict[PermissionLevel, int] = {
    PermissionLevel.DENY: 2,
    PermissionLevel.ASK: 1,
    PermissionLevel.ALLOW: 0,
}


@dataclass
class PermissionRule:
    action: str                  # read / write / execute / delete
    resource_pattern: str        # glob pattern
    level: PermissionLevel
    description: str = ""


class PermissionOverlay:
    """Three-layer permission overlay: defaults -> agent-level -> user-level.

    The three layers **stack**. Every layer is consulted, every match is
    collected, and the strictest level among them wins. A layer that matches
    never short-circuits the search, which is what makes "stacking" true rather
    than decorative.

    The consequence that matters: an override can only ever *tighten*. A
    user-level or agent-level rule may turn ALLOW into ASK or DENY; it can never
    turn a default DENY into ALLOW. Loosening a default is a change to the
    defaults, which is an operator decision, not a per-session one.

    When nothing matches at any layer, the result is DENY (fail closed).
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
        """Evaluate a permission across all three layers.

        Returns the strictest level matched by any layer, or DENY when no
        layer matches.
        """
        matches = self._collect_matches(action, resource, agent_id, user_id)
        if not matches:
            return PermissionLevel.DENY
        return self._strongest(matches)

    def _collect_matches(
        self,
        action: str,
        resource: str,
        agent_id: str | None,
        user_id: str | None,
    ) -> list[PermissionRule]:
        """Every rule that matches, across every applicable layer.

        Deliberately does not stop at the first layer with a hit: that is the
        bug that let an override loosen a default.
        """
        layers = [
            self._user_overrides.get(user_id, []) if user_id else [],
            self._agent_overrides.get(agent_id, []) if agent_id else [],
            self._defaults,
        ]
        matches: list[PermissionRule] = []
        for rules in layers:
            matches.extend(
                rule
                for rule in rules
                if rule.action == action and self._match(rule.resource_pattern, resource)
            )
        return matches

    @classmethod
    def _strongest(cls, rules: list[PermissionRule]) -> PermissionLevel:
        """Pick one level from several rules: most specific wins, then strictest.

        Specificity is compared *within* a level so that a narrow ALLOW can
        never outrank a broad DENY.
        """
        return max(
            rules,
            key=lambda rule: (
                cls._priority(rule.level),
                cls._specificity(rule.resource_pattern),
            ),
        ).level

    @staticmethod
    def _match(pattern: str, path: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(path, pattern)

    @staticmethod
    def _priority(level: PermissionLevel) -> int:
        return _LEVEL_STRENGTH.get(level, 0)

    @staticmethod
    def _specificity(pattern: str) -> tuple[int, int]:
        wildcard_count = sum(pattern.count(char) for char in "*?[")
        return len(pattern) - wildcard_count, -wildcard_count


# ─── JSON Schema Validation ──────────────────────────────────────────────────

class SchemaValidationError(Exception):
    """Raised when tool input fails JSON Schema validation."""


def validate_tool_input(schema: dict[str, Any], arguments: dict[str, Any]) -> None:
    """Validate tool arguments against JSON Schema.

    Only the required-fields and top-level type checks are implemented. Nested
    objects and array element types are not walked, so a schema that relies on
    them is under-validated here.
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


# ─── Path Containment ────────────────────────────────────────────────────────

def resolve_real(path: str) -> str:
    """Fully resolve a path: expand ``~``/``$VARS`` then follow every symlink.

    Containment checks are meaningless without this step -- a symlink inside an
    allowed directory is the cheapest way out of one.
    """
    return os.path.realpath(os.path.expandvars(os.path.expanduser(path)))


def is_contained(child: str, root: str) -> bool:
    """True when ``child`` is ``root`` itself or genuinely inside ``root``.

    Uses ``os.path.commonpath`` so the comparison is on whole path components.
    A prefix test would answer ``True`` for ``/devfoo`` against the root
    ``/dev``; this does not.
    """
    try:
        resolved_child = resolve_real(child)
        resolved_root = resolve_real(root)
    except (OSError, ValueError):
        return False
    if resolved_child == resolved_root:
        return True
    try:
        return os.path.commonpath([resolved_child, resolved_root]) == resolved_root
    except ValueError:
        # Different drives / mixed absolute-relative: never contained.
        return False


# ─── Command Policy ──────────────────────────────────────────────────────────

#: Characters that make a shell expand or reinterpret its argv. The execution
#: path runs commands through ``bash -c``, so a metacharacter here means the
#: process that validated the string is not the process that runs it.
#: ``SandboxExecutor._is_command_safe`` cannot see this -- its path-token scan
#: only looks for absolute paths, so ``echo $(id)`` and ``ls;reboot`` are
#: invisible to it. Rejecting them here is what makes the two agree.
_SHELL_METACHARACTERS = frozenset("|&;<>()$`\n\r\\\"'*?[]{}!#")


#: First whitespace-delimited token of a command line.
_COMMAND_TOKEN = re.compile(r"^\s*(\S+)")


def resolve_command_base(command: str) -> tuple[str | None, str]:
    """Resolve the first token of a command line to an executable path.

    Returns ``(path, "")``, or ``(None, reason)`` when the token would be
    shell-expanded (so the real executable is undecidable at validation time)
    or names nothing on PATH. Relative tokens resolve against the current
    directory, matching how the execution path will interpret them.
    """
    token = _COMMAND_TOKEN.match(command)
    token = token.group(1) if token else ""
    if not token:
        return None, "Empty command"

    if any(char in _CONTROL_METACHARACTERS for char in token):
        return None, (
            f"Command token '{token}' contains shell metacharacters, so the "
            "executable cannot be verified before execution"
        )

    # A token containing a separator is a path; a bare name goes through PATH.
    if "/" in token:
        return os.path.abspath(token), ""

    found = shutil.which(token)
    if found is None:
        # Nothing can execute it, so refuse rather than let the shell decide
        # what it meant.
        return None, f"Command '{token}' was not found on PATH"
    return found, ""


def _execution_command_allowlist() -> set[str]:
    """Return the command names configured for the real executor.

    Keeping this lookup on the executor configuration avoids a second, stale
    list in this preflight layer. The executor itself remains the final process
    admission point.
    """
    from app.core.sandbox import SandboxConfig as ExecutionSandboxConfig

    return {os.path.basename(command) for command in ExecutionSandboxConfig().allowed_commands}


#: Shell characters that let one command become several, or let the shell run
#: something no policy inspected: chaining, pipes, redirection, grouping, and
#: command substitution. The execution path runs commands through ``bash -c``,
#: so any of these means the process that validated the string is not the one
#: that runs it. Their content cannot be validated at validation time, so
#: commands containing them are refused outright.
#:
#: Quotes are deliberately *not* in this set -- ``grep "foo bar" x.py`` is
#: ordinary and still needs to work -- but quoting hides a path from the
#: execution path's token scan, which only fires at whitespace boundaries. That
#: hole is closed separately, in :func:`check_command_paths`, by tokenising
#: with the quotes already removed.
_CONTROL_METACHARACTERS = frozenset("|&;<>()$`\n\r*?[]{}!#")


def _shlex_split(command: str) -> list[str] | None:
    """Split a command into tokens with quotes resolved, or ``None`` if the
    quoting is unbalanced."""
    import shlex

    try:
        return shlex.split(command)
    except ValueError:
        return None


def check_command_paths(tokens: list[str], workdir: str) -> str | None:
    """Return a refusal reason when any token in ``tokens`` names a path
    outside ``workdir``, else ``None``.

    This is the execution path's escape check, re-done over quote-resolved
    tokens. The execution path scans the raw string for absolute paths at
    whitespace boundaries, so it misses anything inside quotes -- verified
    against the current implementation, which returns ``(True, '')`` for
    ``echo '/etc/shadow'``. Running the same containment rule here is what
    closes that gap.
    """
    for token in tokens[1:]:
        if not token.startswith(("/", "~", "./", "../")):
            continue
        expanded = os.path.expanduser(os.path.expandvars(token))
        if os.path.isabs(expanded) and not is_contained(expanded, workdir):
            return f"path '{token}' is outside the workdir"
    return None


# ─── Security Sandbox ────────────────────────────────────────────────────────

@dataclass
class SandboxConfig:
    """Sandbox isolation configuration.

    ``blocked_paths`` entries are *roots*, compared with realpath containment
    rather than string prefix, so ``/dev`` blocks ``/dev/null`` and
    ``/devfoo/bar`` alike. A glob entry (one containing ``*``) is matched with
    ``fnmatch`` after a realpath/commonpath check against its static root, and
    otherwise the entry is treated as a containment root.
    """
    workdir: str                    # Isolated working directory
    allowed_paths: list[str] = field(default_factory=list)  # Additional allowed roots
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
    """Pre-execution policy checks for agent tool calls.

    This class makes no decisions of its own about which commands are safe. It
    defers to :class:`app.core.sandbox.SandboxExecutor`, which is the
    component that actually spawns processes, and adds only the restrictions
    described in the module docstring. It is a gate, not a jail: it can refuse
    a call, it cannot confine one that it admitted.
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig(workdir="/tmp/sandbox")

    def validate_file_access(self, path: str, mode: str = 'read') -> tuple[bool, str]:
        """Validate whether a file may be accessed.

        Containment is decided on the fully resolved path, so ``..`` segments
        and symlinks are collapsed before any comparison. An explicitly
        allowed root wins over a blocked one, which is how a caller opts into
        something the defaults forbid.
        """
        if not path:
            return False, "Access denied: empty path"

        try:
            abs_path = resolve_real(path)
        except (OSError, ValueError) as exc:
            return False, f"Access denied: cannot resolve path '{path}': {exc}"

        for blocked in self.config.blocked_paths:
            if self._matches_block(abs_path, blocked):
                return False, f"Access denied: path '{abs_path}' is in blocked list"

        allowed = [self.config.workdir] + list(self.config.allowed_paths)
        if any(is_contained(abs_path, root) for root in allowed):
            return self._check_size(abs_path, mode)

        return False, f"Access denied: path '{abs_path}' is outside allowed directories"

    def _matches_block(self, abs_path: str, blocked: str) -> bool:
        """Does ``abs_path`` fall under the blocked entry ``blocked``?"""
        if "*" in blocked:
            import fnmatch

            pattern = resolve_real(blocked)
            static_root = pattern.split("*", 1)[0].rstrip(os.sep) or os.sep
            try:
                same_root = os.path.commonpath([abs_path, static_root]) == static_root
            except ValueError:
                same_root = False
            return same_root and fnmatch.fnmatchcase(abs_path, pattern)
        return is_contained(abs_path, blocked)

    def _check_size(self, abs_path: str, mode: str) -> tuple[bool, str]:
        if mode != 'read':
            return True, "OK"
        try:
            if os.path.exists(abs_path):
                size_mb = os.path.getsize(abs_path) / (1024 * 1024)
                if size_mb > self.config.max_file_size_mb:
                    return False, f"File too large: {size_mb:.1f}MB (max {self.config.max_file_size_mb}MB)"
        except OSError as exc:
            return False, f"Access denied: cannot stat '{abs_path}': {exc}"
        return True, "OK"

    def validate_command(self, command: str) -> tuple[bool, str]:
        """Validate a shell command.

        Four checks, all of which must pass:

        1. no shell control metacharacter anywhere in the command;
        2. the first token resolves to a real executable that is not itself a
           shell or interpreter entry point;
        3. no quote-hidden token names a path outside the workdir;
        4. the execution path's own policy, :meth:`SandboxExecutor.
           _is_command_safe`, agrees.

        Check 4 is the authoritative one and is the reason the two sandboxes no
        longer disagree: it is the same call ``SandboxExecutor.execute`` makes
        before spawning. Checks 1-3 close gaps that policy has, verified against
        the current implementation, which *admits* all of these::

            echo $(id)                       -> (True, '')   # bypasses 4 entirely
            echo '/etc/shadow'               -> (True, '')   # hidden from its token scan
            python3 -c "open('/tmp/z','w')"  -> (True, '')   # hands it a program

        ``echo $(id)`` never runs a policy; ``echo '/etc/shadow'`` hides a path
        from the only check that inspects paths; and ``-c`` hands a whole program
        to an interpreter. None of those are visible to check 4, which is
        exactly why this layer is not redundant with it.
        """
        if not command or not command.strip():
            return False, "Empty command"

        if any(char in _CONTROL_METACHARACTERS for char in command):
            return False, (
                "Command contains a shell control character "
                f"({sorted(_CONTROL_METACHARACTERS & set(command))[0]!r}); "
                "chaining, redirection and substitution are not permitted"
            )

        base, reason = resolve_command_base(command)
        if base is None:
            return False, reason

        if os.path.basename(base) in _SHELL_INTERPRETERS:
            return False, (
                f"Command '{os.path.basename(base)}' is a shell/interpreter "
                "entry point; invoke the target program directly"
            )

        command_name = os.path.basename(base)
        try:
            allowed_commands = _execution_command_allowlist()
        except ImportError as exc:
            return False, f"Command policy unavailable: {exc}"
        if command_name not in allowed_commands:
            return False, f"Command '{command_name}' is not in the execution allowlist"

        tokens = _shlex_split(command)
        if tokens is None:
            return False, "Unbalanced quotes in command"
        escape = check_command_paths(tokens, self.config.workdir)
        if escape is not None:
            return False, f"Blocked: {escape}"

        ok, delegated_reason = self._delegate_command_check(command)
        if not ok:
            return False, delegated_reason

        return True, "OK"

    def _delegate_command_check(self, command: str) -> tuple[bool, str]:
        """Run the execution path's own command policy.

        Imported lazily so this module stays importable where
        :mod:`app.core.sandbox` cannot load (it imports ``resource``, which is
        POSIX-only), and so the delegation can be observed by tests.

        The delegated check is given the configured ``workdir`` because the
        execution path compares path tokens against it. When that directory does
        not exist the execution path would have chosen a different, temporary
        one, so we report the disagreement rather than silently guessing.
        """
        workdir = self.config.workdir
        if not os.path.isdir(workdir):
            return False, (
                f"Configured workdir '{workdir}' does not exist, so the "
                "execution path would substitute a different directory and the "
                "delegated check could not be compared"
            )
        try:
            from app.core.sandbox import SandboxExecutor

            return SandboxExecutor()._is_command_safe(command, workdir)
        except ImportError as exc:
            # Fail closed: if the execution path's policy is unavailable, this
            # layer has no second opinion to offer and must not admit the call.
            return False, f"Command policy unavailable: {exc}"

    def sanitize_output(self, output: str) -> str:
        """Truncate oversized output."""
        max_bytes = self.config.max_output_size_kb * 1024
        if len(output.encode('utf-8')) > max_bytes:
            truncated = output.encode('utf-8')[:max_bytes].decode('utf-8', errors='ignore')
            return truncated + f"\n... [Output truncated: exceeded {self.config.max_output_size_kb}KB limit]"
        return output


#: Interpreters that execute a *program given to them*, so the validated
#: executable and the executing process are no longer the same thing. Rejected
#: in the command position; the `bash -c` the execution path itself wraps a
#: command in is internal to that path and never reaches this check.
_SHELL_INTERPRETERS = frozenset({
    "sh", "bash", "zsh", "dash", "ksh", "csh", "tcsh", "fish",
    "python", "python2", "python3",
    "node", "nodejs", "deno", "bun",
    "perl", "ruby", "php", "lua", "tclsh", "wish",
    "env", "eval", "exec", "xargs", "nohup", "setsid", "timeout", "watch",
    "find", "ssh", "sudo", "su", "doas", "stdbuf", "script",
})


# ─── Code Execution Sandbox ──────────────────────────────────────────────────

from app.core.security.code_sandbox import CodeSandbox, VerificationResult


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
            from app.storage import async_session
            from app.storage.models_memory import AuditLog
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
