"""Incremental file editing with diff preview and validation.

- Cline: incremental file modification + JSON Schema validation
- Continue: preview-before-write
"""

from __future__ import annotations

import contextvars
import difflib
import re
from pathlib import Path

import structlog

logger = structlog.get_logger()

# Context-local current agent mode (PLAN / ACT / etc.)
_current_agent_mode: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_agent_mode", default=None
)


def set_current_agent_mode(mode: str | None) -> None:
    """Set the current agent mode for tool execution context."""
    _current_agent_mode.set(mode)


def get_current_agent_mode() -> str | None:
    """Get the current agent mode."""
    return _current_agent_mode.get()


class EditValidationError(Exception):
    """Raised when edit validation fails."""


class FilePatchService:
    """Service for incremental file editing with unified diff support.

    Provides:
    - Unified diff generation using Python's difflib (no external patch command)
    - Edit validation (old_string existence and uniqueness checks)
    - Preview-before-write workflow
    - Patch application with pure-Python implementation
    """

    MIN_UNIQUE_LENGTH = 3
    MAX_AMBIGUITY_COUNT = 100

    @staticmethod
    def create_patch(old_content: str, new_content: str, file_path: str = "") -> str:
        """Create a unified diff string from old and new content.

        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=file_path or "a",
                tofile=file_path or "b",
            )
        )
        return "".join(diff)

    @staticmethod
    def apply_patch_to_file(file_path: str, patch: str) -> tuple[bool, str]:
        """Apply a unified diff patch to a file using pure Python.

        No external patch command dependency.

        Returns (success: bool, message: str).
        """
        try:
            if not Path(file_path).exists():
                return False, f"File not found: {file_path}"

            with open(file_path, encoding="utf-8") as f:
                old_content = f.read()

            new_content = FilePatchService._apply_unified_diff(old_content, patch)
            if new_content is None:
                return False, "Patch application failed: could not parse or apply patch"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            logger.info("patch_applied", file_path=file_path)
            return True, f"Patch applied successfully to {file_path}"
        except Exception as e:
            logger.error("patch_apply_failed", file_path=file_path, error=str(e))
            return False, f"Error applying patch: {str(e)}"

    @staticmethod
    def preview_edit(file_path: str, old_string: str, new_string: str) -> tuple[str, str]:
        """Generate a unified diff preview of an edit without applying it.

        Returns (diff_string, message).
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            if old_string not in content:
                return "", f"old_string not found in {file_path}"

            new_content = content.replace(old_string, new_string, 1)
            diff = FilePatchService.create_patch(content, new_content, file_path)
            return diff, "Preview generated"
        except Exception as e:
            return "", f"Error previewing edit: {str(e)}"

    @staticmethod
    def validate_edit(file_path: str, old_string: str, new_string: str) -> tuple[bool, str]:
        """Validate that old_string exists and is unique enough for safe replacement.

        Checks:
        1. old_string exists in the file
        2. old_string is not too short (min 3 non-whitespace chars)
        3. old_string is not overly ambiguous (appears too many times)

        Returns (valid: bool, message: str).
        """
        try:
            if not Path(file_path).exists():
                return False, f"File not found: {file_path}"

            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            if old_string not in content:
                return False, f"old_string not found in {file_path}"

            stripped = old_string.strip()
            if len(stripped) < FilePatchService.MIN_UNIQUE_LENGTH:
                return (
                    False,
                    f"old_string too short ({len(stripped)} chars, "
                    f"min {FilePatchService.MIN_UNIQUE_LENGTH}). "
                    f"Use a longer, more unique context to avoid accidental replacements.",
                )

            occurrences = content.count(old_string)
            if occurrences > FilePatchService.MAX_AMBIGUITY_COUNT:
                return (
                    False,
                    f"old_string appears {occurrences} times in file "
                    f"(max {FilePatchService.MAX_AMBIGUITY_COUNT}). "
                    f"Use a more unique context.",
                )

            return True, "Edit is valid"
        except Exception as e:
            return False, f"Error validating edit: {str(e)}"

    @staticmethod
    def _apply_unified_diff(old_content: str, patch: str) -> str | None:
        """Apply a unified diff patch to content using pure Python.

        Parses standard unified diff format and applies hunks.
        Returns new content or None if patch application fails.
        """
        old_lines = old_content.splitlines(keepends=True)
        patch_lines = patch.splitlines()

        line_ending = "\n"
        for line in old_lines:
            if line.endswith("\r\n"):
                line_ending = "\r\n"
                break
            if line.endswith("\n"):
                line_ending = "\n"
                break

        hunks = []
        current_hunk = None

        for line in patch_lines:
            if line.startswith("--- ") or line.startswith("+++ "):
                continue
            if line.startswith("@@"):
                if current_hunk is not None:
                    hunks.append(current_hunk)
                match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
                if match:
                    old_start = int(match.group(1))
                    old_count = int(match.group(2)) if match.group(2) else 1
                    current_hunk = {
                        "old_start": old_start,
                        "old_count": old_count,
                        "lines": [],
                    }
                else:
                    current_hunk = {"lines": []}
            elif current_hunk is not None and line:
                if line[0] in (" ", "+", "-"):
                    current_hunk["lines"].append(line)

        if current_hunk is not None:
            hunks.append(current_hunk)

        if not hunks:
            return None

        result_lines = list(old_lines)
        for hunk in reversed(hunks):
            old_start = hunk["old_start"] - 1
            old_count = hunk["old_count"]
            new_hunk_lines = []

            for line in hunk["lines"]:
                if line.startswith(" ") or line.startswith("+"):
                    new_hunk_lines.append(line[1:] + line_ending)

            end = min(old_start + old_count, len(result_lines))
            result_lines[old_start:end] = new_hunk_lines

        return "".join(result_lines)
