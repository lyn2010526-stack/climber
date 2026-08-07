"""Tests for authentication security."""


from app.security.authentication_security import (
    AuthenticationAuditLog,
    AuthenticationEncryption,
    AuthenticationRateLimiter,
    AuthenticationValidator,
)


class TestAuthenticationEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = AuthenticationEncryption.hash_password('testpass')
        assert AuthenticationEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = AuthenticationEncryption.hash_password('testpass')
        assert not AuthenticationEncryption.verify_password('wrong', hashed)


class TestAuthenticationValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert AuthenticationValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not AuthenticationValidator.validate_email('invalid')


class TestAuthenticationRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = AuthenticationRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = AuthenticationRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestAuthenticationAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = AuthenticationAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = AuthenticationAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
