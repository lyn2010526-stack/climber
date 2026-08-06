"""Production-grade security hardening utilities for the agent engine.

Provides input sanitization, rate limiting, secret management, injection
detection, and output encoding using only the Python standard library.
"""

from __future__ import annotations

import html
import re
import secrets
import threading
import time
import urllib.parse
from collections import defaultdict

_SAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9_.\-]")
_SAFE_IDENTIFIER_CHARS = re.compile(r"[^A-Za-z0-9_]")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_NULL_BYTES = re.compile(r"\x00+")
_LEADING_DIGITS = re.compile(r"^\d+")
_CONSECUTIVE_DOTS = re.compile(r"\.+")
_JSON_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_PATH_SEPARATORS = re.compile(r"[\\/]+")

_INJECTION_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "sql": [
        re.compile(r";\s*(drop|delete|insert|update|alter|create|truncate|grant|revoke)\b", re.IGNORECASE),
        re.compile(r"union\s+(all\s+)?select\b", re.IGNORECASE),
        re.compile(r"\b(?:or|and)\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+", re.IGNORECASE),
        re.compile(r"--"),
        re.compile(r"/\*.*\*/"),
        re.compile(r"\bsleep\s*\(", re.IGNORECASE),
        re.compile(r"\binformation_schema\b", re.IGNORECASE),
        re.compile(r"\bexec\s*\(", re.IGNORECASE),
        re.compile(r"\bxp_cmdshell\b", re.IGNORECASE),
    ],
    "command": [
        re.compile(r";\s*(rm|cat|ls|bash|sh|nc|curl|wget|python|node)\b", re.IGNORECASE),
        re.compile(r"`[^`]+`"),
        re.compile(r"\\?\$\s*\("),
        re.compile(r"\|\s*(cat|sh|bash|nc|head|tail)\b", re.IGNORECASE),
        re.compile(r"&&"),
        re.compile(r">>\s*/dev/"),
        re.compile(r">\s*/dev/"),
        re.compile(r"\b(eval|exec|system)\s*\(", re.IGNORECASE),
        re.compile(r"python\s+-c\b", re.IGNORECASE),
        re.compile(r"base64\s+-d\b", re.IGNORECASE),
        re.compile(r"\bsudo\b", re.IGNORECASE),
    ],
    "template": [
        re.compile(r"\{\{\s*.*?\s*\}\}"),
        re.compile(r"\{\%\s*.*?\s*\%\}"),
        re.compile(r"\$\{\s*.*?\s*\}"),
        re.compile(r"<%[-=]?\s*.*?\s*%>"),
    ],
}

_LANGUAGE_ALIASES = {
    "sql": "sql",
    "command": "command",
    "cmd": "command",
    "shell": "command",
    "sh": "command",
    "bash": "command",
    "template": "template",
    "jinja": "template",
    "jinja2": "template",
    "django": "template",
    "mako": "template",
}

_DEFAULT_FILENAME = "unnamed"


class InputSanitizer:
    """Sanitizes untrusted text, filenames, identifiers, and URLs."""

    @staticmethod
    def sanitize_text(value: str, max_length: int = 10000) -> str:
        if not isinstance(value, str):
            value = str(value)
        value = _NULL_BYTES.sub("", value)
        value = _CONTROL_CHARS.sub("", value)
        value = value.strip()
        return value[:max_length]

    @staticmethod
    def sanitize_filename(value: str) -> str:
        parts = _PATH_SEPARATORS.split(value)
        cleaned: list[str] = []
        for part in parts:
            part = _SAFE_FILENAME_CHARS.sub("_", part)
            part = _CONSECUTIVE_DOTS.sub(".", part)
            part = part.lstrip("._")
            if part:
                cleaned.append(part)
        result = "_".join(cleaned)
        return result[:255] or _DEFAULT_FILENAME

    @staticmethod
    def sanitize_sql_identifier(value: str) -> str:
        result = _SAFE_IDENTIFIER_CHARS.sub("_", value)
        result = _LEADING_DIGITS.sub("_", result)
        return result or "_"

    @staticmethod
    def sanitize_url(value: str) -> str | None:
        if not isinstance(value, str):
            return None
        value = value.strip()
        if not value or len(value) > 2048:
            return None
        if _CONTROL_CHARS.search(value):
            return None
        try:
            parsed = urllib.parse.urlparse(value)
        except ValueError:
            return None
        if parsed.scheme.lower() not in ("http", "https"):
            return None
        if not parsed.netloc:
            return None
        return value


class RateLimiter:
    """Sliding-window rate limiter backed by in-memory timestamps per key."""

    def __init__(self, max_requests: int, window_seconds: float):
        if max_requests < 1:
            raise ValueError("max_requests must be a positive integer")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: defaultdict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _prune(self, key: str) -> None:
        cutoff = time.monotonic() - self.window_seconds
        timestamps = self._timestamps[key]
        while timestamps and timestamps[0] <= cutoff:
            timestamps.pop(0)
        if not timestamps:
            self._timestamps.pop(key, None)

    def allow(self, key: str) -> bool:
        with self._lock:
            self._prune(key)
            timestamps = self._timestamps[key]
            if len(timestamps) >= self.max_requests:
                return False
            timestamps.append(time.monotonic())
            return True

    def remaining(self, key: str) -> int:
        with self._lock:
            self._prune(key)
            timestamps = self._timestamps.get(key, [])
            return max(0, self.max_requests - len(timestamps))


class SecretManager:
    """Redacts, validates, and generates secrets."""

    @staticmethod
    def redact(value: str, visible_chars: int = 4) -> str:
        if not isinstance(value, str) or not value:
            return ""
        visible_chars = max(0, visible_chars)
        if len(value) <= visible_chars:
            return "***"
        return f"...{value[-visible_chars:]}"

    @staticmethod
    def is_strong_secret(value: str) -> bool:
        if not isinstance(value, str) or len(value) < 15:
            return False
        has_lower = any(c.islower() for c in value)
        has_upper = any(c.isupper() for c in value)
        has_digit = any(c.isdigit() for c in value)
        has_symbol = any(not c.isalnum() for c in value)
        return has_lower and has_upper and has_digit and has_symbol

    @staticmethod
    def generate_secret(length: int = 32) -> str:
        if length < 1:
            raise ValueError("length must be a positive integer")
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*-_=+"
        return "".join(secrets.choice(alphabet) for _ in range(length))


def detect_injection(text: str, language: str = "sql") -> bool:
    """Return True if the text matches a known injection pattern."""
    if not isinstance(text, str) or not text:
        return False
    language = language.lower()
    lang = _LANGUAGE_ALIASES.get(language, "sql")
    patterns = _INJECTION_PATTERNS[lang]
    return any(pattern.search(text) for pattern in patterns)


class OutputEncoder:
    """Encodes output for safe JSON and HTML rendering."""

    @staticmethod
    def json_safe(value: object) -> str:
        if value is None:
            text = "null"
        elif isinstance(value, bool):
            text = "true" if value else "false"
        elif isinstance(value, str):
            text = value
        else:
            text = str(value)
        text = text.replace("\\", "\\\\").replace('"', '\\"')
        text = _JSON_CONTROL_CHARS.sub(lambda m: f"\\u{ord(m.group()):04x}", text)
        return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    @staticmethod
    def html_escape(value: str) -> str:
        return html.escape(str(value), quote=True)
