"""Security: certificate - Security utilities."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime
from typing import Any


class CertificateEncryption:
    """Encryption utilities."""

    @staticmethod
    def hash_password(password: str, salt: str | None = None) -> str:
        """Hash password."""
        if salt is None:
            salt = secrets.token_hex(16)
        pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f'{salt}${pw_hash.hex()}'

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password."""
        if '$' not in hashed:
            return False
        salt, stored_hash = hashed.split('$', 1)
        pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hmac.compare_digest(pw_hash.hex(), stored_hash)

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate token."""
        return secrets.token_urlsafe(length)


class CertificateValidator:
    """Input validator."""

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_password_strength(password: str) -> dict[str, Any]:
        """Check password strength."""
        score = 0
        if len(password) >= 8: score += 1
        if len(password) >= 12: score += 1
        if re.search(r'[a-z]', password): score += 1
        if re.search(r'[A-Z]', password): score += 1
        if re.search(r'[0-9]', password): score += 1
        if re.search(r'[!@#$%^&*]', password): score += 1
        levels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong']
        return {'score': score, 'strength': levels[min(score // 2, 5)]}


class CertificateRateLimiter:
    """Rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        """Check if allowed."""
        now = datetime.utcnow().timestamp()
        window_start = now - self.window_seconds
        if key not in self._requests:
            self._requests[key] = []
        self._requests[key] = [t for t in self._requests[key] if t > window_start]
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(now)
        return True


class CertificateAuditLog:
    """Audit log."""

    def __init__(self):
        self._entries: list[dict[str, Any]] = []

    def log(self, action: str, actor: str, resource: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        """Log event."""
        entry = {
            'id': secrets.token_hex(16),
            'action': action,
            'actor': actor,
            'resource': resource,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat(),
        }
        self._entries.append(entry)
        return entry

    def query(self, actor: str | None = None, action: str | None = None) -> list[dict[str, Any]]:
        """Query logs."""
        results = self._entries
        if actor:
            results = [e for e in results if e['actor'] == actor]
        if action:
            results = [e for e in results if e['action'] == action]
        return results
