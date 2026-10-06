"""Security primitives shared by domestic provider adapters.

The module deliberately contains no network client. Providers receive opaque
tokens and signed webhook bytes through this contract only.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


def sign_webhook(secret: str, body: bytes, timestamp: int) -> str:
    """Create the ``sha256=`` signature used by the adapter contract."""
    message = f"{timestamp}.".encode() + body
    digest = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_webhook_signature(
    secret: str,
    body: bytes,
    signature: str,
    timestamp: str,
    *,
    now: int | None = None,
    max_skew_seconds: int = 300,
) -> bool:
    """Verify authenticity and freshness without accepting replayed timestamps."""
    if not secret or not signature.startswith("sha256="):
        return False
    try:
        parsed_timestamp = int(timestamp)
    except (TypeError, ValueError):
        return False
    current = int(time.time()) if now is None else now
    if abs(current - parsed_timestamp) > max_skew_seconds:
        return False
    expected = sign_webhook(secret, body, parsed_timestamp)
    return hmac.compare_digest(expected, signature)


@dataclass(frozen=True, slots=True)
class QRToken:
    token: str
    expires_at: datetime
    consumed: bool = False


class QRTokenStore:
    """Bounded in-memory store for short-lived, single-use binding tokens."""

    def __init__(self, *, ttl_seconds: int = 300, max_tokens: int = 1000) -> None:
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be positive")
        self.ttl_seconds = ttl_seconds
        self.max_tokens = max_tokens
        self._tokens: dict[str, QRToken] = {}

    def issue(self, *, now: datetime | None = None) -> QRToken:
        current = now or datetime.now(UTC)
        self._purge(current)
        if len(self._tokens) >= self.max_tokens:
            raise RuntimeError("qr token capacity exhausted")
        token = secrets.token_urlsafe(32)
        record = QRToken(token=token, expires_at=current + timedelta(seconds=self.ttl_seconds))
        self._tokens[token] = record
        return record

    def consume(self, token: str, *, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        record = self._tokens.get(token)
        if record is None or record.consumed or current >= record.expires_at:
            self._tokens.pop(token, None)
            return False
        self._tokens[token] = QRToken(record.token, record.expires_at, consumed=True)
        return True

    def _purge(self, now: datetime) -> None:
        for token, record in list(self._tokens.items()):
            if now >= record.expires_at or record.consumed:
                self._tokens.pop(token, None)
