"""Tests for security_audit security module."""


from app.security.security_audit_security import (
    SecurityAuditAccessControl,
    SecurityAuditAuditTrail,
    SecurityAuditEncryption,
    SecurityAuditInputValidator,
    SecurityAuditPasswordHasher,
    SecurityAuditRateLimiter,
    SecurityAuditSessionManager,
    SecurityAuditTokenManager,
)


class TestSecurityAuditPasswordHasher:
    """Tests for password hashing."""

    def test_hash_and_verify(self):
        hashed = SecurityAuditPasswordHasher.hash_password("testpass123")
        assert SecurityAuditPasswordHasher.verify_password('testpass123', hashed)

    def test_wrong_password(self):
        hashed = SecurityAuditPasswordHasher.hash_password("testpass123")
        assert not SecurityAuditPasswordHasher.verify_password('wrongpass', hashed)

    def test_invalid_hash(self):
        assert not SecurityAuditPasswordHasher.verify_password('test', 'invalid')


class TestSecurityAuditTokenManager:
    """Tests for token management."""

    def test_generate_token(self):
        token = SecurityAuditTokenManager.generate_token()
        assert len(token) > 0

    def test_generate_api_key(self):
        key = SecurityAuditTokenManager.generate_api_key()
        assert key.startswith('ak_')

    def test_generate_csrf(self):
        token = SecurityAuditTokenManager.generate_csrf_token()
        assert len(token) == 64


class TestSecurityAuditInputValidator:
    """Tests for input validation."""

    def test_validate_email_valid(self):
        assert SecurityAuditInputValidator.validate_email('test@example.com')

    def test_validate_email_invalid(self):
        assert not SecurityAuditInputValidator.validate_email('not-an-email')

    def test_validate_url_valid(self):
        assert SecurityAuditInputValidator.validate_url('https://example.com')

    def test_validate_uuid(self):
        assert SecurityAuditInputValidator.validate_uuid('12345678-1234-5678-1234-567812345678')

    def test_sanitize_html(self):
        result = SecurityAuditInputValidator.sanitize_html("<script>alert('xss')</script>Hello")
        assert '<script>' not in result

    def test_password_strength(self):
        result = SecurityAuditInputValidator.validate_password_strength("weak")
        assert result["score"] < 3
        result = SecurityAuditInputValidator.validate_password_strength("Str0ng!Pass#2024")
        assert result["score"] >= 5


class TestSecurityAuditRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = SecurityAuditRateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = SecurityAuditRateLimiter(max_requests=2, window_seconds=60)
        assert limiter.is_allowed('user1')
        assert limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')

    def test_get_remaining(self):
        limiter = SecurityAuditRateLimiter(max_requests=5, window_seconds=60)
        limiter.is_allowed('user1')
        assert limiter.get_remaining('user1') == 4


class TestSecurityAuditEncryption:
    """Tests for encryption utilities."""

    def test_hash_data(self):
        result = SecurityAuditEncryption.hash_data("test data")
        assert len(result) == 64

    def test_hmac_sign(self):
        sig = SecurityAuditEncryption.hmac_sign("data", "key")
        assert len(sig) == 64

    def test_verify_hmac(self):
        sig = SecurityAuditEncryption.hmac_sign("data", "key")
        assert SecurityAuditEncryption.verify_hmac('data', 'key', sig)

    def test_derive_key(self):
        key, salt = SecurityAuditEncryption.derive_key('password')
        assert len(key) == 32
        assert len(salt) == 16


class TestSecurityAuditAuditTrail:
    """Tests for audit trail."""

    def test_log_event(self):
        trail = SecurityAuditAuditTrail()
        entry = trail.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query_by_actor(self):
        trail = SecurityAuditAuditTrail()
        trail.log('create', 'user1', 'r1')
        trail.log('delete', 'user2', 'r2')
        results = trail.query(actor='user1')
        assert len(results) == 1

    def test_get_stats(self):
        trail = SecurityAuditAuditTrail()
        trail.log('create', 'user1', 'r1')
        trail.log('create', 'user1', 'r2')
        stats = trail.get_stats()
        assert stats['total_entries'] == 2


class TestSecurityAuditAccessControl:
    """Tests for access control."""

    def test_check_permission_any(self):
        assert SecurityAuditAccessControl.check_permission(['admin', 'user'], ['admin'])

    def test_check_permission_all(self):
        assert SecurityAuditAccessControl.check_permission(['admin', 'user'], ['admin', 'user'], require_all=True)

    def test_is_owner(self):
        assert SecurityAuditAccessControl.is_owner(1, 1)
        assert not SecurityAuditAccessControl.is_owner(1, 2)

    def test_can_access_owner(self):
        assert SecurityAuditAccessControl.can_access(1, ['user'], 1, None, None)

    def test_can_access_admin(self):
        assert SecurityAuditAccessControl.can_access(2, ['admin'], 1, None, None)


class TestSecurityAuditSessionManager:
    """Tests for session management."""

    def test_create_and_get_session(self):
        mgr = SecurityAuditSessionManager()
        sid = mgr.create_session(1)
        session = mgr.get_session(sid)
        assert session is not None
        assert session['user_id'] == 1

    def test_invalidate_session(self):
        mgr = SecurityAuditSessionManager()
        sid = mgr.create_session(1)
        assert mgr.invalidate_session(sid)
        assert mgr.get_session(sid) is None

    def test_invalidate_user_sessions(self):
        mgr = SecurityAuditSessionManager()
        mgr.create_session(1)
        mgr.create_session(1)
        count = mgr.invalidate_user_sessions(1)
        assert count == 2
