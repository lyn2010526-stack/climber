"""Security module: security_audit - Security utilities and protections."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger()


class SecurityAuditPasswordHasher:
    """Secure password hashing."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with salt."""
        salt = secrets.token_hex(16)
        pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return f"{salt}${pw_hash.hex()}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash."""
        if "$" not in hashed:
            return False
        salt, stored_hash = hashed.split("$", 1)
        pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return hmac.compare_digest(pw_hash.hex(), stored_hash)


class SecurityAuditTokenManager:
    """Token generation and validation."""

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate secure random token."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_api_key(prefix: str = "ak") -> str:
        """Generate API key with prefix."""
        random_part = secrets.token_hex(16)
        return f"{prefix}_{random_part}"

    @staticmethod
    def generate_csrf_token() -> str:
        """Generate CSRF token."""
        return secrets.token_hex(32)


class SecurityAuditInputValidator:
    """Input validation utilities."""

    @staticmethod
    def sanitize_html(text: str) -> str:
        """Remove potentially dangerous HTML."""
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)
        text = re.sub(r"on\w+\s*=", "", text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format."""
        pattern = r"^https?://[\w.-]+(:\d+)?(/.*)?$"
        return bool(re.match(pattern, url))

    @staticmethod
    def validate_uuid(value: str) -> bool:
        """Validate UUID format."""
        pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return bool(re.match(pattern, value, re.IGNORECASE))

    @staticmethod
    def sanitize_sql(value: str) -> str:
        """Basic SQL injection prevention."""
        dangerous = [";", "--", "/*", "*/", "xp_", "DROP", "DELETE", "INSERT", "UPDATE"]
        result = value
        for d in dangerous:
            result = result.replace(d, "")
        return result

    @staticmethod
    def validate_password_strength(password: str) -> dict[str, Any]:
        """Check password strength."""
        score = 0
        feedback = []
        if len(password) >= 8:
            score += 1
        else:
            feedback.append("At least 8 characters")
        if len(password) >= 12:
            score += 1
        if re.search(r"[a-z]", password):
            score += 1
        else:
            feedback.append("Add lowercase letters")
        if re.search(r"[A-Z]", password):
            score += 1
        else:
            feedback.append("Add uppercase letters")
        if re.search(r"[0-9]", password):
            score += 1
        else:
            feedback.append("Add numbers")
        if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            score += 1
        else:
            feedback.append("Add special characters")
        levels = ["Very Weak", "Weak", "Fair", "Good", "Strong", "Very Strong"]
        return {"score": score, "strength": levels[min(score // 2, 5)], "feedback": feedback}


class SecurityAuditRateLimiter:
    """In-memory rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed."""
        now = time.time()
        window_start = now - self.window_seconds
        if key not in self._requests:
            self._requests[key] = []
        self._requests[key] = [t for t in self._requests[key] if t > window_start]
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(now)
        return True

    def get_remaining(self, key: str) -> int:
        """Get remaining requests."""
        now = time.time()
        window_start = now - self.window_seconds
        if key not in self._requests:
            return self.max_requests
        recent = [t for t in self._requests[key] if t > window_start]
        return max(0, self.max_requests - len(recent))

    def get_reset_time(self, key: str) -> datetime:
        """Get time when rate limit resets."""
        if key not in self._requests or not self._requests[key]:
            return datetime.utcnow()
        oldest = min(self._requests[key])
        return datetime.fromtimestamp(oldest + self.window_seconds)


class SecurityAuditEncryption:
    """Symmetric encryption utilities."""

    @staticmethod
    def derive_key(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
        """Derive encryption key from password."""
        if salt is None:
            salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return key, salt

    @staticmethod
    def hash_data(data: str, algorithm: str = 'sha256') -> str:
        """Hash data with specified algorithm."""
        hasher = hashlib.new(algorithm)
        hasher.update(data.encode())
        return hasher.hexdigest()

    @staticmethod
    def hmac_sign(data: str, key: str, algorithm: str = 'sha256') -> str:
        """Generate HMAC signature."""
        h = hmac.new(key.encode(), data.encode(), algorithm)
        return h.hexdigest()

    @staticmethod
    def verify_hmac(data: str, key: str, signature: str) -> bool:
        """Verify HMAC signature."""
        expected = SecurityAuditEncryption.hmac_sign(data, key)
        return hmac.compare_digest(expected, signature)


class SecurityAuditAuditTrail:
    """Audit trail logging."""

    def __init__(self):
        self._entries: list[dict[str, Any]] = []

    def log(
        self,
        action: str,
        actor: str,
        resource: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Log an audit event."""
        entry = {
            "id": secrets.token_hex(16),
            "action": action,
            "actor": actor,
            "resource": resource,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._entries.append(entry)
        return entry

    def query(
        self,
        actor: str | None = None,
        action: str | None = None,
        resource: str | None = None,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Query audit trail."""
        results = self._entries
        if actor:
            results = [e for e in results if e["actor"] == actor]
        if action:
            results = [e for e in results if e["action"] == action]
        if resource:
            results = [e for e in results if e["resource"] == resource]
        if since:
            results = [e for e in results if datetime.fromisoformat(e['timestamp']) >= since]
        return results

    def get_stats(self) -> dict[str, Any]:
        """Get audit trail statistics."""
        actions = {}
        actors = {}
        for entry in self._entries:
            actions[entry['action']] = actions.get(entry['action'], 0) + 1
            actors[entry['actor']] = actors.get(entry['actor'], 0) + 1
        return {
            'total_entries': len(self._entries),
            'unique_actors': len(actors),
            'action_counts': actions,
            'top_actors': dict(sorted(actors.items(), key=lambda x: -x[1])[:10]),
        }


class SecurityAuditAccessControl:
    """Access control utilities."""

    @staticmethod
    def check_permission(
        user_roles: list[str],
        required_roles: list[str],
        require_all: bool = False,
    ) -> bool:
        """Check if user has required roles."""
        if not required_roles:
            return True
        if require_all:
            return all(role in user_roles for role in required_roles)
        return any(role in user_roles for role in required_roles)

    @staticmethod
    def is_owner(user_id: int, resource_owner_id: int) -> bool:
        """Check if user owns resource."""
        return user_id == resource_owner_id

    @staticmethod
    def can_access(
        user_id: int,
        user_roles: list[str],
        resource_owner_id: int,
        resource_org_id: int | None,
        user_org_id: int | None,
    ) -> bool:
        """Check resource access."""
        if SecurityAuditAccessControl.is_owner(user_id, resource_owner_id):
            return True
        if 'admin' in user_roles:
            return True
        return bool(resource_org_id and user_org_id and resource_org_id == user_org_id and 'org_admin' in user_roles)


class SecurityAuditSessionManager:
    """Session management."""

    def __init__(self, session_ttl: int = 3600):
        self.session_ttl = session_ttl
        self._sessions: dict[str, dict[str, Any]] = {}

    def create_session(self, user_id: int, metadata: dict[str, Any] | None = None) -> str:
        """Create new session."""
        session_id = secrets.token_urlsafe(32)
        self._sessions[session_id] = {
            'user_id': user_id,
            'metadata': metadata or {},
            'created_at': time.time(),
            'last_accessed': time.time(),
        }
        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session if valid."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        if time.time() - session['created_at'] > self.session_ttl:
            del self._sessions[session_id]
            return None
        session['last_accessed'] = time.time()
        return session

    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def invalidate_user_sessions(self, user_id: int) -> int:
        """Invalidate all sessions for user."""
        to_remove = [sid for sid, s in self._sessions.items() if s['user_id'] == user_id]
        for sid in to_remove:
            del self._sessions[sid]
        return len(to_remove)

    def cleanup_expired(self) -> int:
        """Remove expired sessions."""
        now = time.time()
        expired = [sid for sid, s in self._sessions.items() if now - s['created_at'] > self.session_ttl]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)
