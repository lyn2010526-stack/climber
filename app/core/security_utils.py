"""Security utilities for path validation, shell analysis, and input sanitization.

Implements defense-in-depth for local file operations:
- Path traversal prevention
- Shell command risk analysis
- Prompt injection detection
- Sandbox mode enforcement
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Security violation detected."""
    pass


class PathValidator:
    """Validates file paths to prevent directory traversal attacks."""

    def __init__(self, allowed_roots: list[str] | None = None):
        """Initialize with allowed root directories.

        If no roots specified, allows current working directory.
        """
        if allowed_roots:
            self._roots = [Path(r).resolve() for r in allowed_roots]
        else:
            self._roots = [Path.cwd().resolve()]

    def validate(self, path: str) -> Path:
        """Validate a path is within allowed roots.

        Returns resolved path if valid.
        Raises SecurityError if path escapes allowed roots.
        """
        resolved = Path(path).resolve()

        # Check for path traversal
        for root in self._roots:
            try:
                resolved.relative_to(root)
                return resolved
            except ValueError:
                continue

        # Also check with expanded user
        expanded = Path(os.path.expanduser(path)).resolve()
        for root in self._roots:
            try:
                expanded.relative_to(root)
                return expanded
            except ValueError:
                continue

        raise SecurityError(
            f"Path '{path}' is outside allowed directories: "
            f"{[str(r) for r in self._roots]}"
        )

    def is_safe(self, path: str) -> bool:
        """Check if path is safe without raising."""
        try:
            self.validate(path)
            return True
        except SecurityError:
            return False

    def add_root(self, root: str):
        """Add an allowed root directory."""
        resolved = Path(root).resolve()
        if resolved not in self._roots:
            self._roots.append(resolved)


class ShellRiskAnalyzer:
    """Analyzes shell commands for dangerous patterns."""

    # Commands that are always blocked
    BLOCKED_COMMANDS = {
        "rm": ["-rf /", "-rf ~", "-rf /*", "-fr /"],
        "mkfs": [""],
        "dd": ["if=/dev/zero of=/dev/sda", "if=/dev/random of=/dev/sda"],
        "chmod": ["-R 777 /", "777 /"],
        "chown": ["-R root /"],
    }

    # Patterns that require confirmation
    RISKY_PATTERNS = [
        (r"rm\s+-rf?\s+", "Recursive delete"),
        (r"curl.*\|\s*(ba)?sh", "Download and execute"),
        (r"wget.*\|\s*(ba)?sh", "Download and execute"),
        (r"git\s+push\s+--force", "Force push"),
        (r"git\s+push\s+-f", "Force push"),
        (r"sudo\s+", "Privileged execution"),
        (r"su\s+-", "Switch user"),
        (r">\s*/dev/", "Direct device write"),
        (r"mkfs\.", "Format filesystem"),
        (r":\(\)\{.*\};", "Fork bomb"),
        (r"chmod\s+-R\s+777", "World-writable recursion"),
    ]

    # Read-only commands (safe)
    READONLY_COMMANDS = {
        "cat", "head", "tail", "less", "more", "grep", "find", "ls",
        "pwd", "wc", "diff", "file", "stat", "which", "echo",
        "python3 -c", "node -e",
    }

    @classmethod
    def analyze(cls, command: str) -> dict:
        """Analyze a shell command for risks.

        Returns dict with:
        - risk_level: "safe", "low", "medium", "high", "blocked"
        - concerns: list of concern descriptions
        - allowed: bool
        """
        concerns = []
        risk_level = "safe"

        # Check blocked patterns
        for cmd, dangerous_args in cls.BLOCKED_COMMANDS.items():
            if command.strip().startswith(cmd):
                for arg_pattern in dangerous_args:
                    if arg_pattern and arg_pattern in command:
                        return {
                            "risk_level": "blocked",
                            "concerns": [f"Dangerous: {cmd} {arg_pattern}"],
                            "allowed": False,
                        }

        # Check risky patterns
        for pattern, description in cls.RISKY_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                concerns.append(description)
                risk_level = "high"

        # Check if purely read-only
        cmd_base = command.strip().split()[0] if command.strip() else ""
        if cmd_base in {"cat", "head", "tail", "less", "more", "grep", "find", "ls", "pwd", "wc", "diff", "file", "stat", "which", "echo"}:
            risk_level = "safe"
            concerns = []

        return {
            "risk_level": risk_level,
            "concerns": concerns,
            "allowed": risk_level != "blocked",
        }

    @classmethod
    def is_safe(cls, command: str) -> bool:
        """Quick check if command is safe."""
        return cls.analyze(command)["allowed"]


class InputSanitizer:
    """Sanitizes user input to prevent prompt injection."""

    # Patterns that might indicate prompt injection attempts
    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"disregard\s+(your\s+)?(system\s+)?prompt",
        r"you\s+are\s+now\s+(a\s+)?",
        r"new\s+persona",
        r"system\s*:\s*you\s+are",
        r"<\s*/\s*instructions\s*>",
        r"\[\s*system\s*\]",
    ]

    @classmethod
    def check_injection(cls, text: str) -> dict:
        """Check for potential prompt injection.

        Returns dict with injection risk assessment.
        """
        concerns = []
        text_lower = text.lower()

        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                concerns.append(f"Potential injection pattern: {pattern}")

        return {
            "risk_level": "high" if concerns else "safe",
            "concerns": concerns,
            "safe": len(concerns) == 0,
        }

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Sanitize input text."""
        # Remove null bytes
        text = text.replace("\x00", "")

        # Limit consecutive newlines (prevent context breaking)
        text = re.sub(r"\n{5,}", "\n\n\n\n", text)

        return text.strip()


class SandboxMode:
    """Enforces sandbox restrictions on file operations."""

    def __init__(self, sandbox_root: str):
        self.root = Path(sandbox_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._path_validator = PathValidator(allowed_roots=[str(self.root)])

    def resolve(self, path: str) -> Path:
        """Resolve a path within the sandbox."""
        p = Path(path)
        if not p.is_absolute():
            p = self.root / path
        return self._path_validator.validate(str(p))

    def read(self, path: str) -> str:
        """Read a file within sandbox."""
        full_path = self.resolve(path)
        return full_path.read_text(encoding="utf-8")

    def write(self, path: str, content: str):
        """Write a file within sandbox."""
        full_path = self.resolve(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")

    def list_files(self, pattern: str = "**/*") -> list[str]:
        """List files in sandbox."""
        return [str(p.relative_to(self.root)) for p in self.root.glob(pattern) if p.is_file()]
