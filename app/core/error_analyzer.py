"""Error analysis module for the auto-debug loop.

"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ErrorType(str, Enum):
    """Classification of error categories for auto-debug."""

    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    PERMISSION_ERROR = "permission_error"
    IMPORT_ERROR = "import_error"
    NETWORK_ERROR = "network_error"
    FILE_NOT_FOUND = "file_not_found"
    TIMEOUT = "timeout"
    AUTHENTICATION_ERROR = "authentication_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"


@dataclass
class ErrorAnalysis:
    """Structured error information extracted from tool execution results."""

    error_type: ErrorType
    message: str
    file_path: str | None = None
    line_number: int | None = None
    cause: str | None = None
    raw_error: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "cause": self.cause,
            "confidence": self.confidence,
        }


class ErrorAnalyzer:
    """Analyze tool execution results and extract structured error information.

    Supports common patterns:
    - Python tracebacks
    - Shell command errors
    - HTTP errors
    - Generic error strings
    """

    _PYTHON_TRACEBACK_RE = re.compile(
        r"Traceback \(most recent call last\):\n(.*?)(?:\n[A-Z][a-zA-Z]+Error: |\n[A-Z][a-zA-Z]+Exception: )(.*)",
        re.DOTALL,
    )
    _PYTHON_LINE_RE = re.compile(r"File \"(.+?)\", line (\d+)")
    _SHELL_ERROR_RE = re.compile(
        r"(?:sh:|bash:|zsh:).*?(?:command not found|No such file or directory|Permission denied|"
        r"exit code \d+|Operation not permitted|Is a directory|Not a directory|"
        r"Text file busy|Device or resource busy|Too many open files)"
    )
    _HTTP_ERROR_RE = re.compile(
        r"HTTP \d{3}|status code \d{3}|\d{3} (Forbidden|Unauthorized|Not Found|Internal Server Error|Bad Request)"
    )
    _PERMISSION_ERROR_RE = re.compile(
        r"Permission denied|EACCES|permission denied|operation not permitted"
    )
    _TIMEOUT_ERROR_RE = re.compile(
        r"timed out|timeout|TimeLimitExceeded|deadline exceeded"
    )
    _FILE_NOT_FOUND_RE = re.compile(
        r"FileNotFoundError|No such file or directory|does not exist|not found"
    )
    _NETWORK_ERROR_RE = re.compile(
        r"Connection refused|Connection reset|Network is unreachable|Name or service not known|"
        r"getaddrinfo ENOTFOUND|ECONNREFUSED|ETIMEDOUT"
    )

    def analyze(self, error_message: str, context: dict[str, Any] | None = None) -> ErrorAnalysis:
        """Parse an error message and return a structured ErrorAnalysis."""
        context = context or {}
        raw = error_message.strip()
        if not raw:
            return ErrorAnalysis(error_type=ErrorType.UNKNOWN, message="empty error", raw_error="")

        file_path: str | None = None
        line_number: int | None = None
        cause = raw

        python_match = self._PYTHON_TRACEBACK_RE.search(raw)
        if python_match:
            tb_body, error_msg = python_match.group(1), python_match.group(2)
            file_match = self._PYTHON_LINE_RE.findall(tb_body)
            if file_match:
                file_path, line_str = file_match[-1]
                try:
                    line_number = int(line_str)
                except ValueError:
                    line_number = None
            cause = error_msg.strip()
            error_type = self._classify_python_error(cause)
            return ErrorAnalysis(
                error_type=error_type,
                message=cause,
                file_path=file_path,
                line_number=line_number,
                cause=cause,
                raw_error=raw,
                context=context,
            )

        if self._PERMISSION_ERROR_RE.search(raw):
            return ErrorAnalysis(
                error_type=ErrorType.PERMISSION_ERROR,
                message=raw,
                cause=raw,
                raw_error=raw,
                context=context,
            )
        if self._FILE_NOT_FOUND_RE.search(raw) and "command not found" not in raw.lower():
            return ErrorAnalysis(
                error_type=ErrorType.FILE_NOT_FOUND,
                message=raw,
                cause=raw,
                raw_error=raw,
                context=context,
            )
        if self._TIMEOUT_ERROR_RE.search(raw):
            return ErrorAnalysis(
                error_type=ErrorType.TIMEOUT,
                message=raw,
                cause=raw,
                raw_error=raw,
                context=context,
            )
        if self._NETWORK_ERROR_RE.search(raw):
            return ErrorAnalysis(
                error_type=ErrorType.NETWORK_ERROR,
                message=raw,
                cause=raw,
                raw_error=raw,
                context=context,
            )
        if self._HTTP_ERROR_RE.search(raw):
            return ErrorAnalysis(
                error_type=ErrorType.AUTHENTICATION_ERROR if "401" in raw or "403" in raw else ErrorType.UNKNOWN,
                message=raw,
                cause=raw,
                raw_error=raw,
                context=context,
            )

        if self._SHELL_ERROR_RE.search(raw):
            error_type = ErrorType.RUNTIME_ERROR
            if "Permission denied" in raw or "EACCES" in raw:
                error_type = ErrorType.PERMISSION_ERROR
            elif "command not found" in raw:
                error_type = ErrorType.SYNTAX_ERROR
            elif "No such file or directory" in raw:
                error_type = ErrorType.FILE_NOT_FOUND
            return ErrorAnalysis(
                error_type=error_type,
                message=raw,
                cause=raw,
                raw_error=raw,
                context=context,
            )

        return ErrorAnalysis(
            error_type=ErrorType.UNKNOWN,
            message=raw,
            cause=raw,
            raw_error=raw,
            context=context,
        )

    def _classify_python_error(self, error_msg: str) -> ErrorType:
        if "SyntaxError" in error_msg or "IndentationError" in error_msg:
            return ErrorType.SYNTAX_ERROR
        if "ImportError" in error_msg or "ModuleNotFoundError" in error_msg:
            return ErrorType.IMPORT_ERROR
        if "PermissionError" in error_msg or "Permission denied" in error_msg:
            return ErrorType.PERMISSION_ERROR
        if "FileNotFoundError" in error_msg:
            return ErrorType.FILE_NOT_FOUND
        if "TimeoutError" in error_msg or "asyncio.TimeoutError" in error_msg:
            return ErrorType.TIMEOUT
        if "ConnectionError" in error_msg or "HTTPError" in error_msg or "RequestException" in error_msg:
            return ErrorType.NETWORK_ERROR
        if "AuthenticationError" in error_msg or "401" in error_msg or "403" in error_msg:
            return ErrorType.AUTHENTICATION_ERROR
        if "ValueError" in error_msg or "TypeError" in error_msg or "KeyError" in error_msg or "IndexError" in error_msg:
            return ErrorType.VALIDATION_ERROR
        return ErrorType.RUNTIME_ERROR
