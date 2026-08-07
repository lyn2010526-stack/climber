#!/usr/bin/env python3
"""Generate security and utility modules."""

from __future__ import annotations

from pathlib import Path

BASE = Path("/workspace/agent-engine")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def gen_security(name: str, class_name: str) -> str:
    return (
        '"""Security module: ' + name + ' - Security utilities and protections."""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "import hashlib\n"
        "import hmac\n"
        "import os\n"
        "import re\n"
        "import secrets\n"
        "import time\n"
        "from typing import Any, Optional\n"
        "from datetime import datetime, timedelta\n"
        "from dataclasses import dataclass, field\n"
        "\n"
        "import structlog\n"
        "\n"
        'logger = structlog.get_logger()\n'
        "\n"
        "\n"
        "class " + class_name + 'PasswordHasher:\n'
        '    """Secure password hashing."""\n'
        "\n"
        '    @staticmethod\n'
        '    def hash_password(password: str) -> str:\n'
        '        """Hash password with salt."""\n'
        '        salt = secrets.token_hex(16)\n'
        '        pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)\n'
        '        return f"{salt}${pw_hash.hex()}"\n'
        "\n"
        "    @staticmethod\n"
        '    def verify_password(password: str, hashed: str) -> bool:\n'
        '        """Verify password against hash."""\n'
        '        if "$" not in hashed:\n'
        "            return False\n"
        '        salt, stored_hash = hashed.split("$", 1)\n'
        '        pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)\n'
        "        return hmac.compare_digest(pw_hash.hex(), stored_hash)\n"
        "\n"
        "\n"
        "class " + class_name + 'TokenManager:\n'
        '    """Token generation and validation."""\n'
        "\n"
        "    @staticmethod\n"
        "    def generate_token(length: int = 32) -> str:\n"
        '        """Generate secure random token."""\n'
        "        return secrets.token_urlsafe(length)\n"
        "\n"
        "    @staticmethod\n"
        '    def generate_api_key(prefix: str = "ak") -> str:\n'
        '        """Generate API key with prefix."""\n'
        '        random_part = secrets.token_hex(16)\n'
        '        return f"{prefix}_{random_part}"\n'
        "\n"
        "    @staticmethod\n"
        "    def generate_csrf_token() -> str:\n"
        '        """Generate CSRF token."""\n'
        "        return secrets.token_hex(32)\n"
        "\n"
        "\n"
        "class " + class_name + 'InputValidator:\n'
        '    """Input validation utilities."""\n'
        "\n"
        "    @staticmethod\n"
        "    def sanitize_html(text: str) -> str:\n"
        '        """Remove potentially dangerous HTML."""\n'
        '        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)\n'
        '        text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)\n'
        '        text = re.sub(r"on\\\\w+\\\\s*=", "", text, flags=re.IGNORECASE)\n'
        "        return text\n"
        "\n"
        "    @staticmethod\n"
        "    def validate_email(email: str) -> bool:\n"
        '        """Validate email format."""\n'
        '        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,}$"\n'
        "        return bool(re.match(pattern, email))\n"
        "\n"
        "    @staticmethod\n"
        "    def validate_url(url: str) -> bool:\n"
        '        """Validate URL format."""\n'
        '        pattern = r"^https?://[\\\\w.-]+(:\\\\d+)?(/.*)?$"\n'
        "        return bool(re.match(pattern, url))\n"
        "\n"
        "    @staticmethod\n"
        "    def validate_uuid(value: str) -> bool:\n"
        '        """Validate UUID format."""\n'
        '        pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"\n'
        "        return bool(re.match(pattern, value, re.IGNORECASE))\n"
        "\n"
        "    @staticmethod\n"
        "    def sanitize_sql(value: str) -> str:\n"
        '        """Basic SQL injection prevention."""\n'
        '        dangerous = [";", "--", "/*", "*/", "xp_", "DROP", "DELETE", "INSERT", "UPDATE"]\n'
        "        result = value\n"
        "        for d in dangerous:\n"
        "            result = result.replace(d, '')\n"
        "        return result\n"
        "\n"
        "    @staticmethod\n"
        "    def validate_password_strength(password: str) -> dict[str, Any]:\n"
        '        """Check password strength."""\n'
        "        score = 0\n"
        "        feedback = []\n"
        "        if len(password) >= 8:\n"
        "            score += 1\n"
        "        else:\n"
        '            feedback.append("At least 8 characters")\n'
        "        if len(password) >= 12:\n"
        "            score += 1\n"
        '        if re.search(r"[a-z]", password):\n'
        "            score += 1\n"
        "        else:\n"
        '            feedback.append("Add lowercase letters")\n'
        '        if re.search(r"[A-Z]", password):\n'
        "            score += 1\n"
        "        else:\n"
        '            feedback.append("Add uppercase letters")\n'
        '        if re.search(r"[0-9]", password):\n'
        "            score += 1\n"
        "        else:\n"
        '            feedback.append("Add numbers")\n'
        '        if re.search(r"[!@#$%^&*(),.?\\\":{}|<>]", password):\n'
        "            score += 1\n"
        "        else:\n"
        '            feedback.append("Add special characters")\n'
        '        levels = ["Very Weak", "Weak", "Fair", "Good", "Strong", "Very Strong"]\n'
        '        return {"score": score, "strength": levels[min(score // 2, 5)], "feedback": feedback}\n'
        "\n"
        "\n"
        "class " + class_name + 'RateLimiter:\n'
        '    """In-memory rate limiter."""\n'
        "\n"
        "    def __init__(self, max_requests: int = 100, window_seconds: int = 60):\n"
        "        self.max_requests = max_requests\n"
        "        self.window_seconds = window_seconds\n"
        "        self._requests: dict[str, list[float]] = {}\n"
        "\n"
        "    def is_allowed(self, key: str) -> bool:\n"
        '        """Check if request is allowed."""\n'
        "        now = time.time()\n"
        "        window_start = now - self.window_seconds\n"
        "        if key not in self._requests:\n"
        "            self._requests[key] = []\n"
        "        self._requests[key] = [t for t in self._requests[key] if t > window_start]\n"
        "        if len(self._requests[key]) >= self.max_requests:\n"
        "            return False\n"
        "        self._requests[key].append(now)\n"
        "        return True\n"
        "\n"
        "    def get_remaining(self, key: str) -> int:\n"
        '        """Get remaining requests."""\n'
        "        now = time.time()\n"
        "        window_start = now - self.window_seconds\n"
        "        if key not in self._requests:\n"
        "            return self.max_requests\n"
        "        recent = [t for t in self._requests[key] if t > window_start]\n"
        "        return max(0, self.max_requests - len(recent))\n"
        "\n"
        "    def get_reset_time(self, key: str) -> datetime:\n"
        '        """Get time when rate limit resets."""\n'
        "        if key not in self._requests or not self._requests[key]:\n"
        "            return datetime.utcnow()\n"
        "        oldest = min(self._requests[key])\n"
        "        return datetime.fromtimestamp(oldest + self.window_seconds)\n"
        "\n"
        "\n"
        "class " + class_name + 'Encryption:\n'
        '    """Symmetric encryption utilities."""\n'
        "\n"
        "    @staticmethod\n"
        "    def derive_key(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:\n"
        '        """Derive encryption key from password."""\n'
        "        if salt is None:\n"
        "            salt = os.urandom(16)\n"
        "        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)\n"
        "        return key, salt\n"
        "\n"
        "    @staticmethod\n"
        "    def hash_data(data: str, algorithm: str = 'sha256') -> str:\n"
        '        """Hash data with specified algorithm."""\n'
        "        hasher = hashlib.new(algorithm)\n"
        "        hasher.update(data.encode())\n"
        "        return hasher.hexdigest()\n"
        "\n"
        "    @staticmethod\n"
        "    def hmac_sign(data: str, key: str, algorithm: str = 'sha256') -> str:\n"
        '        """Generate HMAC signature."""\n'
        "        h = hmac.new(key.encode(), data.encode(), algorithm)\n"
        "        return h.hexdigest()\n"
        "\n"
        "    @staticmethod\n"
        "    def verify_hmac(data: str, key: str, signature: str) -> bool:\n"
        '        """Verify HMAC signature."""\n'
        "        expected = " + class_name + "Encryption.hmac_sign(data, key)\n"
        "        return hmac.compare_digest(expected, signature)\n"
        "\n"
        "\n"
        "class " + class_name + 'AuditTrail:\n'
        '    """Audit trail logging."""\n'
        "\n"
        "    def __init__(self):\n"
        "        self._entries: list[dict[str, Any]] = []\n"
        "\n"
        "    def log(\n"
        "        self,\n"
        "        action: str,\n"
        "        actor: str,\n"
        "        resource: str,\n"
        "        details: dict[str, Any] | None = None,\n"
        "    ) -> dict[str, Any]:\n"
        '        """Log an audit event."""\n'
        "        entry = {\n"
        '            "id": secrets.token_hex(16),\n'
        '            "action": action,\n'
        '            "actor": actor,\n'
        '            "resource": resource,\n'
        '            "details": details or {},\n'
        '            "timestamp": datetime.utcnow().isoformat(),\n'
        "        }\n"
        "        self._entries.append(entry)\n"
        "        return entry\n"
        "\n"
        "    def query(\n"
        "        self,\n"
        "        actor: str | None = None,\n"
        "        action: str | None = None,\n"
        "        resource: str | None = None,\n"
        "        since: datetime | None = None,\n"
        "    ) -> list[dict[str, Any]]:\n"
        '        """Query audit trail."""\n'
        "        results = self._entries\n"
        "        if actor:\n"
        '            results = [e for e in results if e["actor"] == actor]\n'
        "        if action:\n"
        '            results = [e for e in results if e["action"] == action]\n'
        "        if resource:\n"
        '            results = [e for e in results if e["resource"] == resource]\n'
        "        if since:\n"
        "            results = [e for e in results if datetime.fromisoformat(e['timestamp']) >= since]\n"
        "        return results\n"
        "\n"
        "    def get_stats(self) -> dict[str, Any]:\n"
        '        """Get audit trail statistics."""\n'
        "        actions = {}\n"
        "        actors = {}\n"
        "        for entry in self._entries:\n"
        "            actions[entry['action']] = actions.get(entry['action'], 0) + 1\n"
        "            actors[entry['actor']] = actors.get(entry['actor'], 0) + 1\n"
        "        return {\n"
        "            'total_entries': len(self._entries),\n"
        "            'unique_actors': len(actors),\n"
        "            'action_counts': actions,\n"
        "            'top_actors': dict(sorted(actors.items(), key=lambda x: -x[1])[:10]),\n"
        "        }\n"
        "\n"
        "\n"
        "class " + class_name + 'AccessControl:\n'
        '    """Access control utilities."""\n'
        "\n"
        "    @staticmethod\n"
        "    def check_permission(\n"
        "        user_roles: list[str],\n"
        "        required_roles: list[str],\n"
        "        require_all: bool = False,\n"
        "    ) -> bool:\n"
        '        """Check if user has required roles."""\n'
        "        if not required_roles:\n"
        "            return True\n"
        "        if require_all:\n"
        "            return all(role in user_roles for role in required_roles)\n"
        "        return any(role in user_roles for role in required_roles)\n"
        "\n"
        "    @staticmethod\n"
        "    def is_owner(user_id: int, resource_owner_id: int) -> bool:\n"
        '        """Check if user owns resource."""\n'
        "        return user_id == resource_owner_id\n"
        "\n"
        "    @staticmethod\n"
        "    def can_access(\n"
        "        user_id: int,\n"
        "        user_roles: list[str],\n"
        "        resource_owner_id: int,\n"
        "        resource_org_id: int | None,\n"
        "        user_org_id: int | None,\n"
        "    ) -> bool:\n"
        '        """Check resource access."""\n'
        "        if " + class_name + "AccessControl.is_owner(user_id, resource_owner_id):\n"
        "            return True\n"
        "        if 'admin' in user_roles:\n"
        "            return True\n"
        "        if resource_org_id and user_org_id and resource_org_id == user_org_id:\n"
        "            if 'org_admin' in user_roles:\n"
        "                return True\n"
        "        return False\n"
        "\n"
        "\n"
        "class " + class_name + 'SessionManager:\n'
        '    """Session management."""\n'
        "\n"
        "    def __init__(self, session_ttl: int = 3600):\n"
        "        self.session_ttl = session_ttl\n"
        "        self._sessions: dict[str, dict[str, Any]] = {}\n"
        "\n"
        "    def create_session(self, user_id: int, metadata: dict[str, Any] | None = None) -> str:\n"
        '        """Create new session."""\n'
        "        session_id = secrets.token_urlsafe(32)\n"
        "        self._sessions[session_id] = {\n"
        "            'user_id': user_id,\n"
        "            'metadata': metadata or {},\n"
        "            'created_at': time.time(),\n"
        "            'last_accessed': time.time(),\n"
        "        }\n"
        "        return session_id\n"
        "\n"
        "    def get_session(self, session_id: str) -> dict[str, Any] | None:\n"
        '        """Get session if valid."""\n'
        "        session = self._sessions.get(session_id)\n"
        "        if not session:\n"
        "            return None\n"
        "        if time.time() - session['created_at'] > self.session_ttl:\n"
        "            del self._sessions[session_id]\n"
        "            return None\n"
        "        session['last_accessed'] = time.time()\n"
        "        return session\n"
        "\n"
        "    def invalidate_session(self, session_id: str) -> bool:\n"
        '        """Invalidate session."""\n'
        "        if session_id in self._sessions:\n"
        "            del self._sessions[session_id]\n"
        "            return True\n"
        "        return False\n"
        "\n"
        "    def invalidate_user_sessions(self, user_id: int) -> int:\n"
        '        """Invalidate all sessions for user."""\n'
        "        to_remove = [sid for sid, s in self._sessions.items() if s['user_id'] == user_id]\n"
        "        for sid in to_remove:\n"
        "            del self._sessions[sid]\n"
        "        return len(to_remove)\n"
        "\n"
        "    def cleanup_expired(self) -> int:\n"
        '        """Remove expired sessions."""\n'
        "        now = time.time()\n"
        "        expired = [sid for sid, s in self._sessions.items() if now - s['created_at'] > self.session_ttl]\n"
        "        for sid in expired:\n"
        "            del self._sessions[sid]\n"
        "        return len(expired)\n"
    )


def gen_security_test(name: str, class_name: str) -> str:
    return (
        '"""Tests for ' + name + ' security module."""\n'
        "\n"
        "import pytest\n"
        "import time\n"
        "\n"
        "from app.security." + name + "_security import (\n"
        "    " + class_name + "PasswordHasher,\n"
        "    " + class_name + "TokenManager,\n"
        "    " + class_name + "InputValidator,\n"
        "    " + class_name + "RateLimiter,\n"
        "    " + class_name + "Encryption,\n"
        "    " + class_name + "AuditTrail,\n"
        "    " + class_name + "AccessControl,\n"
        "    " + class_name + "SessionManager,\n"
        ")\n"
        "\n"
        "\n"
        "class Test" + class_name + 'PasswordHasher:\n'
        '    """Tests for password hashing."""\n'
        "\n"
        "    def test_hash_and_verify(self):\n"
        '        hashed = ' + class_name + 'PasswordHasher.hash_password("testpass123")\n'
        "        assert " + class_name + "PasswordHasher.verify_password('testpass123', hashed)\n"
        "\n"
        "    def test_wrong_password(self):\n"
        '        hashed = ' + class_name + 'PasswordHasher.hash_password("testpass123")\n'
        "        assert not " + class_name + "PasswordHasher.verify_password('wrongpass', hashed)\n"
        "\n"
        "    def test_invalid_hash(self):\n"
        "        assert not " + class_name + "PasswordHasher.verify_password('test', 'invalid')\n"
        "\n"
        "\n"
        "class Test" + class_name + 'TokenManager:\n'
        '    """Tests for token management."""\n'
        "\n"
        "    def test_generate_token(self):\n"
        "        token = " + class_name + "TokenManager.generate_token()\n"
        "        assert len(token) > 0\n"
        "\n"
        "    def test_generate_api_key(self):\n"
        "        key = " + class_name + "TokenManager.generate_api_key()\n"
        "        assert key.startswith('ak_')\n"
        "\n"
        "    def test_generate_csrf(self):\n"
        "        token = " + class_name + "TokenManager.generate_csrf_token()\n"
        "        assert len(token) == 64\n"
        "\n"
        "\n"
        "class Test" + class_name + 'InputValidator:\n'
        '    """Tests for input validation."""\n'
        "\n"
        "    def test_validate_email_valid(self):\n"
        "        assert " + class_name + "InputValidator.validate_email('test@example.com')\n"
        "\n"
        "    def test_validate_email_invalid(self):\n"
        "        assert not " + class_name + "InputValidator.validate_email('not-an-email')\n"
        "\n"
        "    def test_validate_url_valid(self):\n"
        "        assert " + class_name + "InputValidator.validate_url('https://example.com')\n"
        "\n"
        "    def test_validate_uuid(self):\n"
        "        assert " + class_name + "InputValidator.validate_uuid('12345678-1234-5678-1234-567812345678')\n"
        "\n"
        "    def test_sanitize_html(self):\n"
        '        result = ' + class_name + "InputValidator.sanitize_html(\"<script>alert('xss')</script>Hello\")\n"
        "        assert '<script>' not in result\n"
        "\n"
        "    def test_password_strength(self):\n"
        '        result = ' + class_name + 'InputValidator.validate_password_strength("weak")\n'
        '        assert result["score"] < 3\n'
        '        result = ' + class_name + 'InputValidator.validate_password_strength("Str0ng!Pass#2024")\n'
        '        assert result["score"] >= 5\n'
        "\n"
        "\n"
        "class Test" + class_name + 'RateLimiter:\n'
        '    """Tests for rate limiter."""\n'
        "\n"
        "    def test_within_limit(self):\n"
        "        limiter = " + class_name + "RateLimiter(max_requests=5, window_seconds=60)\n"
        "        for _ in range(5):\n"
        "            assert limiter.is_allowed('user1')\n"
        "\n"
        "    def test_exceeds_limit(self):\n"
        "        limiter = " + class_name + "RateLimiter(max_requests=2, window_seconds=60)\n"
        "        assert limiter.is_allowed('user1')\n"
        "        assert limiter.is_allowed('user1')\n"
        "        assert not limiter.is_allowed('user1')\n"
        "\n"
        "    def test_get_remaining(self):\n"
        "        limiter = " + class_name + "RateLimiter(max_requests=5, window_seconds=60)\n"
        "        limiter.is_allowed('user1')\n"
        "        assert limiter.get_remaining('user1') == 4\n"
        "\n"
        "\n"
        "class Test" + class_name + 'Encryption:\n'
        '    """Tests for encryption utilities."""\n'
        "\n"
        "    def test_hash_data(self):\n"
        '        result = ' + class_name + 'Encryption.hash_data("test data")\n'
        "        assert len(result) == 64\n"
        "\n"
        "    def test_hmac_sign(self):\n"
        '        sig = ' + class_name + 'Encryption.hmac_sign("data", "key")\n'
        "        assert len(sig) == 64\n"
        "\n"
        "    def test_verify_hmac(self):\n"
        '        sig = ' + class_name + 'Encryption.hmac_sign("data", "key")\n'
        "        assert " + class_name + "Encryption.verify_hmac('data', 'key', sig)\n"
        "\n"
        "    def test_derive_key(self):\n"
        "        key, salt = " + class_name + "Encryption.derive_key('password')\n"
        "        assert len(key) == 32\n"
        "        assert len(salt) == 16\n"
        "\n"
        "\n"
        "class Test" + class_name + 'AuditTrail:\n'
        '    """Tests for audit trail."""\n'
        "\n"
        "    def test_log_event(self):\n"
        "        trail = " + class_name + "AuditTrail()\n"
        "        entry = trail.log('create', 'user1', 'resource1')\n"
        "        assert entry['action'] == 'create'\n"
        "\n"
        "    def test_query_by_actor(self):\n"
        "        trail = " + class_name + "AuditTrail()\n"
        "        trail.log('create', 'user1', 'r1')\n"
        "        trail.log('delete', 'user2', 'r2')\n"
        "        results = trail.query(actor='user1')\n"
        "        assert len(results) == 1\n"
        "\n"
        "    def test_get_stats(self):\n"
        "        trail = " + class_name + "AuditTrail()\n"
        "        trail.log('create', 'user1', 'r1')\n"
        "        trail.log('create', 'user1', 'r2')\n"
        "        stats = trail.get_stats()\n"
        "        assert stats['total_entries'] == 2\n"
        "\n"
        "\n"
        "class Test" + class_name + 'AccessControl:\n'
        '    """Tests for access control."""\n'
        "\n"
        "    def test_check_permission_any(self):\n"
        "        assert " + class_name + "AccessControl.check_permission(['admin', 'user'], ['admin'])\n"
        "\n"
        "    def test_check_permission_all(self):\n"
        "        assert " + class_name + "AccessControl.check_permission(['admin', 'user'], ['admin', 'user'], require_all=True)\n"
        "\n"
        "    def test_is_owner(self):\n"
        "        assert " + class_name + "AccessControl.is_owner(1, 1)\n"
        "        assert not " + class_name + "AccessControl.is_owner(1, 2)\n"
        "\n"
        "    def test_can_access_owner(self):\n"
        "        assert " + class_name + "AccessControl.can_access(1, ['user'], 1, None, None)\n"
        "\n"
        "    def test_can_access_admin(self):\n"
        "        assert " + class_name + "AccessControl.can_access(2, ['admin'], 1, None, None)\n"
        "\n"
        "\n"
        "class Test" + class_name + 'SessionManager:\n'
        '    """Tests for session management."""\n'
        "\n"
        "    def test_create_and_get_session(self):\n"
        "        mgr = " + class_name + "SessionManager()\n"
        "        sid = mgr.create_session(1)\n"
        "        session = mgr.get_session(sid)\n"
        "        assert session is not None\n"
        "        assert session['user_id'] == 1\n"
        "\n"
        "    def test_invalidate_session(self):\n"
        "        mgr = " + class_name + "SessionManager()\n"
        "        sid = mgr.create_session(1)\n"
        "        assert mgr.invalidate_session(sid)\n"
        "        assert mgr.get_session(sid) is None\n"
        "\n"
        "    def test_invalidate_user_sessions(self):\n"
        "        mgr = " + class_name + "SessionManager()\n"
        "        sid1 = mgr.create_session(1)\n"
        "        sid2 = mgr.create_session(1)\n"
        "        count = mgr.invalidate_user_sessions(1)\n"
        "        assert count == 2\n"
    )


def main() -> None:
    all_files: dict[str, str] = {}

    security_modules = [
        ("authentication", "Authentication"),
        ("authorization", "Authorization"),
        ("data_protection", "DataProtection"),
        ("threat_detection", "ThreatDetection"),
        ("vulnerability_scan", "VulnerabilityScan"),
        ("compliance_check", "ComplianceCheck"),
        ("incident_response", "IncidentResponse"),
        ("security_monitoring", "SecurityMonitoring"),
        ("penetration_test", "PenetrationTest"),
        ("security_audit", "SecurityAudit"),
    ]

    print(f"Generating {len(security_modules)} security modules with tests...")

    for name, class_name in security_modules:
        content = gen_security(name, class_name)
        all_files[f"app/security/{name}_security.py"] = content

        test_content = gen_security_test(name, class_name)
        all_files[f"tests/test_{name}_security.py"] = test_content

    print(f"Writing {len(all_files)} files...")
    for path_str, content in all_files.items():
        write_file(BASE / path_str, content)

    print(f"Done! Generated {len(all_files)} files across {len(security_modules)} security modules.")


if __name__ == "__main__":
    main()
